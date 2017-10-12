import discord
from discord.ext import commands
from .utils.chat_formatting import escape_mass_mentions, italics, pagify
from urllib.parse import quote_plus
import datetime
import time
import aiohttp
import asyncio
import sqlite3

class Rosterize:
    """
    Rosterize: a cog for making rosters
    
    Written by Aaron "Xenocidel" Liao for osu! UCI

    """

    def __init__(self, bot):
        self.bot = bot
        # self.rosters = {}
        
    def setvars(self, ctx):
        message = ctx.message
        margs = str.split(message.content)
        conn = sqlite3.connect('rosterize.db')
        c = conn.cursor()
        return (message, margs, conn, c)
        
    def dbclose(self, conn):
        conn.close()

    def inrosters(self, c, sid, rname):
        """
        Checks if an entry with the same roster name in a specific server
        exists in the rosters table
        """
        queryelements = ["SELECT 1 FROM rosters WHERE sid = ", sid,
                " AND rname = ", rname]
        query = "".join(queryelements)
        c.execute(query)
        if c.fetchone() is 1:
            return True
        return False

    def inattendees(self, c, sid, rname, uid):
        """
        Checks if a user is in the attendees table for the specific server
        and roster name pair
        """
        queryelements = ["SELECT 1 FROM attendees WHERE sid = ", sid,
                " AND rname = ", rname, " AND attendee_uid = ", uid]
        query = "".join(queryelements)
        c.execute(query)
        if c.fetchone() is 1:
            return True
        return False


    def addattendee(self, c, sid, rname, uid):
        """
        Adds a user to attendees table. If a duplicate entry is inserted,
        SQL will raise an exception due to table constraints.

        raises: DatabaseError
        """
        c.execute("INSERT INTO attendees VALUES (?,?,?)", sid, rname, attendee_uid)
        c.commit()

    def removeattendee(self, c, sid, rname, uid=None):
        queryelements = ["DELETE FROM attendees WHERE sid = ", sid,
                " AND rname = ", rname]

        if uid is not None:
            queryelements.append(" AND attendee_uid = ")
            queryelements.append(uid)
        query = "".join(queryelements)
        c.execute(query)
        c.commit()

    def newroster(self, c, sid, rname, author_uid):
        c.execute("INSERT INTO rosters VALUES (?,?,?)", sid, rname, author_uid)
        c.commit()

    def delroster(self, c, sid, rname):
        removeattendee(c, sid, rname)  # removes all attendees from roster
        queryelements = ["DELETE FROM rosters WHERE sid = ", sid,
                " AND rname = ", rname]
        query = "".join(queryelements)
        c.execute(query)
        c.commit()

    async def rosterdetail(self, c, sid, rname):
        """
        Returns a dict with the following values:
          author: roster author ID
          a_count: number of attendees in that roster
          a_list: list of attendees for that roster
        """
        ans = {}
        attendees = []
        queryelements = ["SELECT author_uid FROM rosters WHERE sid = ", sid,
                " AND rname = ", rname]
        query = "".join(queryelements)
        c.execute(query)
        ans['author'] = c.fetchone()[0]  # author ID
        queryelements = ["SELECT attendee_uid FROM attendees WHERE sid = ",
                sid, " AND rname = ", rname]
        query = "".join(queryelements)
        qresult = c.execute(query)
        ans['a_count'] = len(qresult)  # number of attendees
        for row in qresult:
            attendees.append(await self.get_user_info(row[0])
        ans['a_list'] = attendees  # list of attendees (User type)        

    @commands.command(aliases=["cr", "nr"], pass_context=True, no_pm=True)
    async def createroster(self, ctx):
        """Creates a new roster

        Usage:
        createroster <roster name>
        """
        t = setvars(ctx)
        message, margs, conn, c = t
        
        if len(margs) is not 2:
            await self.bot.say("No roster name specified")
        elif inrosters(c, message.server.id, margs[1]):
        # if margs[1] in self.rosters:
            await self.bot.say(margs[1] + ' already exists')
        else:
            newroster(c, message.server.id, margs[1], message.author.id)
            # self.rosters[margs[1]] = []
            await self.bot.say('Created new roster called ' + margs[1] + '. Type ,jr ' + margs[1] + ' to join')
        
        dbclose(conn)

    @commands.command(aliases=["jr"], pass_context=True, no_pm=True)
    async def joinroster(self, ctx):
        """Joins an existing roster

        Usage:
        joinroster <roster name>
        """
        t = setvars(ctx)
        message, margs, conn, c = t
        if len(margs) is not 2:
            await self.bot.say("No roster name specified. To see list of rosters, use the rosterstatus (rs) command")
        elif not intable(c, message.server.id, margs[1]):
            await self.bot.say(margs[1] + " does not exist")
        else:
            try:
                addattendee(c, message.server.id, margs[1], message.author.id)
                await self.bot.say('Added ' + 
                    message.author.display_name + ' to ' + margs[1])
            except DatabaseError:
                await self.bot.say(message.author.display_name +
                        ' already in roster ' + margs[1])
        dbclose(conn)

    @commands.command(aliases=["ur"], pass_context=True, no_pm=True)
    async def unroster(self, ctx):
        """Unrosters from an existing roster

        Usage:
        unroster <roster name>
        """
        t = setvars(ctx)
        message, margs, conn, c = t
        if len(margs) is not 2:
            await self.bot.say("No roster name specified. To see list of rosters, use the rosterstatus (rs) command")
        elif not intable(c, message.server.id, margs[1]):
            await self.bot.say(margs[1] + " does not exist")
        else:
            if not inattendees(c, message.server.id, margs[1], message.author.id):
                await self.bot.say(message.author.display_name + ' not in roster ' +
                        margs[1])
            else:
                removeattendee(c, message.server.id, margs[1], message.author.id)
                await self.bot.say('Removed ' + message.author.display_name +
                    ' from ' + margs[1])
        dbclose(conn)

    @commands.command(aliases=["dr"], pass_context=True, no_pm=True)
    async def delroster(self, ctx):
        """Deletes an existing roster. Only the roster author can delete(TODO)

        Usage:
        delroster <roster name>
        """
        t = setvars(ctx)
        message, margs, conn, c = t
        
        if len(margs) is not 2:
            await self.bot.say("No roster name specified")
        elif not intable(c, message.server.id, margs[1]):
            await self.bot.say(margs[1] + " does not exist")
        else:
            delroster(c, message.server.id, margs[1])
            await self.bot.say(margs[1] + " deleted")
        dbclose(conn)

    @commands.command(aliases=["rs", "lr"], pass_context=True, no_pm=True)
    async def rosterstatus(self, ctx):
        """Displays members of a roster, or all rosters and member counts

        Usage:
        rosterstatus
        rosterstatus <roster name>
        """
        t = setvars(ctx)
        message, margs, conn, c = t
        
        if len(margs) is 1:,
            # Display all rosters and their respective attendee counts
            out_elements = ["There are ", str(len(self.rosters.keys())),
                    " rosters\n"]
            for roster in self.rosters.keys():
                out_elements.append(roster)
                out_elements.append(": ")
                out_elements.append(str(len(self.rosters[roster])))
                out_elements.append("\n")
            await self.bot.say("".join(out_elements))
        elif len(margs) is 2:
            # Display roster author, attendee count, and attendees
            if not intable(c, message.server.id, margs[1]):
                await self.bot.say(margs[1] + " does not exist")
            else:
                r = rosterdetail(c, message.server.id, margs[1])
                em = discord.Embed()
                em.title = "Roster status of " + margs[1]
                em.set_footer(text = "Created by " + r.author)
                out_elements = [": ",
                        str(len(self.rosters[margs[1]])), "\n"]
                for user in self.rosters[margs[1]]:
                    out_elements.append(user.display_name)
                    out_elements.append(" ")
                await self.bot.say("".join(out_elements))
        dbclose(conn)

def setup(bot):
    n = Rosterize(bot)
    #bot.add_listener(n.check_poll_votes, "on_message")
    bot.add_cog(n)
