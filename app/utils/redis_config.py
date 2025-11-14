from fastapi import Request


async def set_key(key:str, value:str, exp:int, request:Request):
    r = request.app.state.redis
    r.setex(key, exp, value)
    
    
async def get_key(key:str, request:Request):
    r = request.app.state.redis
    value = r.get(key)
    return value.decode() if value else None