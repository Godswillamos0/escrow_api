import uuid
from enum import Enum
from sqlalchemy import (
    Column, String, Numeric, DateTime, func, Boolean, ForeignKey
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import relationship
from .database import Base

# Enums
class TransactionType(Enum):
    DEPOSIT = 'DEPOSIT'
    WITHDRAWAL = 'WITHDRAWAL'
    TRANSFER = 'TRANSFER'
    ESCROW_FUND = 'ESCROW_FUND'
    ESCROW_RELEASE = 'ESCROW_RELEASE'
    REFUND = 'REFUND'

class TransactionStatus(Enum):
    PENDING = 'PENDING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    REVERSED = 'REVERSED'

class EscrowStatus(Enum):
    FUNDED = 'FUNDED'
    RELEASED = 'RELEASED'
    REFUNDED = 'REFUNDED'
    PENDING = 'PENDING'
    DISPUTED = 'DISPUTED'
    CANCELLED = 'CANCELLED'

class CurrencyCode(Enum):
    NGN = 'NGN'
    USD = 'USD'
    EUR = 'EUR'
    GBP = 'GBP'


# User
class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String, index=True)
    email = Column(String, index=True)

    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")

    # Use string-based foreign key references
    escrows_as_client = relationship(
        "Escrow",
        foreign_keys="[Escrow.client_id]",  # string so it’s lazily resolved
        back_populates="client"
    )
    escrows_as_merchant = relationship(
        "Escrow",
        foreign_keys="[Escrow.merchant_id]",
        back_populates="merchant"
    )

    banks = relationship("WithdrawalBank", back_populates="user")



# Wallet
class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"))
    balance = Column(Numeric(18, 2), nullable=False, default=0.00)
    currency = Column(SqlEnum(CurrencyCode), nullable=False, default=CurrencyCode.NGN)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="wallets")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")


# Wallet Transaction
class WalletTransaction(Base):
    __tablename__ = 'wallet_transactions'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String(36), ForeignKey('wallets.id'), nullable=False, index=True)
    transaction_type = Column(SqlEnum(TransactionType), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    status = Column(SqlEnum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    reference_code = Column(String(64), unique=True, nullable=False, default=lambda: f"TXN-{uuid.uuid4().hex[:10].upper()}")
    timestamp = Column(DateTime, default=func.now())

    wallet = relationship("Wallet", back_populates="transactions")


# Escrow
class Escrow(Base):
    __tablename__ = 'escrow'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(36), ForeignKey('users.source_id'), nullable=False, index=True)#
    merchant_id = Column(String(36), ForeignKey('users.source_id'), nullable=False, index=True)#
    client_agree = Column(Boolean, default=False)
    merchant_agree = Column(Boolean, default=False)
    amount = Column(Numeric(18, 2), nullable=False)
    status = Column(SqlEnum(EscrowStatus), nullable=False, default=EscrowStatus.FUNDED)
    created_at = Column(DateTime, default=func.now())
    finalized_at = Column(DateTime, nullable=True)

    client = relationship("User", foreign_keys=[client_id], back_populates="escrows_as_client")
    merchant = relationship("User", foreign_keys=[merchant_id], back_populates="escrows_as_merchant")


# Withdrawal Bank
class WithdrawalBank(Base):
    __tablename__ = "banks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    bank_code = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    account_name = Column(String, nullable=False)

    user = relationship("User", back_populates="banks")
