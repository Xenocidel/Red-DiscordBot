import discord
from discord.ext import commands
from .utils.chat_formatting import escape_mass_mentions, italics, pagify
from urllib.parse import quote_plus
import aiohttp
import asyncio

class Mahjong:
    """
    Mahjong: a cog for showing Mahjong hands and asking what-would-you-discard questions
    
    Written by Aaron "Xenocidel" Liao

    """

    def __init__(self, bot):
        self.bot = bot
        # self.rosters = {}
        
    def setvars(self, ctx):
        message = ctx.message
        margs = str.split(message.content)
        return (message, margs)

    def parsehand(self, hand):
        """
        Parses a hand string or returns an error string
        14-tile hands will have a space added to indicate tsumo tile
        Example 1
            Input: 57m1799p89s11335z2s
            Output: :5m::7m::1p::7p::9p::9p::8s::9s::1z::1z::3z::3z::5z: :2s:
        Example 2
            Input: 57mm
            Output: eDuplicate alpha character
        Example 3
            Input: 3m123
            Output: eNo alpha character found
        """
        out_string = "eUnknown Error"
        return out_string

    @commands.command(aliases=["mj"], pass_context=True, no_pm=True)
    async def mahjong(self, ctx):
        """Converts a hand string into emojis to display the hand pictorally

        Usage:
        mahjong <hand string>
        Example hand string 57m1799p89s11335z2s
        """
        t = self.setvars(ctx)
        message, margs = t
        em = discord.Embed()
        error = True

        if len(margs) is not 2:
            # Error
            em.title = "Invalid number of arguments"
            em.description = "Usage: >mahjong <hand string> Example hand string: 57m1799p89s11335z2s"
        elif len(margs[1]) > 30:
            # Error
            em.title = "Hand size too long (max 30 characters)"
            em.description = "Usage: >mahjong <hand string> Example hand string: 57m1799p89s11335z2s"
        else:
            out_string = self.parsehand(margs[1])
            if out_string[0] is "e":
                # Start of an error string
                em.title = "Error parsing hand string"
                em.description = out_string[1:]
            else:
                error = False
                em.description = out_string
                em.set_footer(text = "http://tenhou.net/2/?q=" + margs[1])
        await self.bot.say(embed = em)
        if not error:
            # Delete the user's message
            await message.delete

def setup(bot):
    n = Mahjong(bot)
    #bot.add_listener(n.check_poll_votes, "on_message")
    bot.add_cog(n)
