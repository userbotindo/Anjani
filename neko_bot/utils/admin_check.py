"""Admin check utils"""

async def adminlist(client, chat_id):
    """This Function to get admin list."""
    admins = []
    async for i in client.iter_chat_members(chat_id):
        if i.status in ["administrator", "creator"]:
            admins.append(i.user.id)
    return admins
