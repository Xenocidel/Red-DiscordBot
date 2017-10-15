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
    
    Written by Aaron "Xenocidel" Liao

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

    def intable(self, c, sid, rname):
        """
        Checks if an entry with the same roster name in a specific server
        exists in the rosters table
        """
        queryelements = ["SELECT 1 FROM rosters WHERE sid = '", sid,
                "' AND rname = '", rname, "'"]
        query = "".join(queryelements)
        for row in c.execute(query):
            if row[0] == 1:
                return True
            return False

    def inattendees(self, c, sid, rname, uid):
        """
        Checks if a user is in the attendees table for the specific server
        and roster name pair
        """
        queryelements = ["SELECT 1 FROM attendees WHERE sid = '", sid,
                "' AND rname = '", rname, "' AND attendee_uid = '", uid, "'"]
        query = "".join(queryelements)
        for row in c.execute(query):
            if row[0] == 1:
                return True
            return False


    def addattendee(self, conn, c, sid, rname, uid):
        """
        Adds a user to attendees table. If a duplicate entry is inserted,
        SQL will raise an exception due to table constraints.

        raises: DatabaseError
        """
        c.execute("INSERT INTO attendees VALUES (?,?,?)", (sid, rname, uid))
        conn.commit()

    def removeattendee(self, conn, c, sid, rname, uid=None):
        queryelements = ["DELETE FROM attendees WHERE sid = '", sid,
                "' AND rname = '", rname, "'"]

        if uid is not None:
            queryelements.append(" AND attendee_uid = '")
            queryelements.append(uid)
            queryelements.append("'")
        query = "".join(queryelements)
        c.execute(query)
        conn.commit()

    def newroster(self, conn, c, sid, rname, author_uid):
        c.execute("INSERT INTO rosters VALUES (?,?,?)", (sid, rname, author_uid))
        conn.commit()

    def del_db_roster(self, conn, c, sid, rname):
        self.removeattendee(conn, c, sid, rname)  # removes all attendees from roster
        queryelements = ["DELETE FROM rosters WHERE sid = '", sid,
                "' AND rname = '", rname, "'"]
        query = "".join(queryelements)
        c.execute(query)
        conn.commit()

    def rosterdetail(self, c, sid, rname=None):
        """
        Returns a dict with the following values:
          author: roster author ID
          a_count: number of attendees in that roster
          a_list: list of attendees for that roster
        """
        ans = {}
        attendees = []
        rosters = {}
        if rname != None:
            # return specific roster's author, attendees, and count
            queryelements = ["SELECT author_uid FROM rosters WHERE sid = '", sid,
                "' AND rname = '", rname, "'"]
            query = "".join(queryelements)
            c.execute(query)
            ans['author'] = c.fetchone()[0]  # author ID
            queryelements = ["SELECT attendee_uid FROM attendees WHERE sid = '",
                    sid, "' AND rname = '", rname, "'"]
            query = "".join(queryelements)
            qresult = c.execute(query)
            a_count = 0  # number of attendees
            for row in qresult:
                attendees.append(row[0])
                a_count += 1
            ans['a_count'] = a_count
            ans['a_list'] = attendees  # list of attendees' IDs        
        else:
            # return all rosters in a specified server and the attendee counts
            # TODO fix this
            queryelements = ["SELECT rname FROM rosters WHERE rosters.sid = '",
                sid, "'"]
            query = "".join(queryelements)
            qresult = c.execute(query)
            r_count = 0
            for row in qresult:
                rosters[row[0]] = 0
                r_count += 1
            queryelements = ["SELECT rname, count(rname) FROM attendees WHERE attendees.sid = '",
                    sid, "' GROUP BY rname"]
            query = "".join(queryelements)
            qresult = c.execute(query)
            for row in qresult:
                rosters[row[0]] = row[1]
            ans['r_count'] = r_count
            ans['r_list'] = rosters
        return ans

    @commands.command(aliases=["cr", "nr"], pass_context=True, no_pm=True)
    async def createroster(self, ctx):
        """Creates a new roster

        Usage:
        createroster <roster name>
        """
        t = self.setvars(ctx)
        message, margs, conn, c = t
        
        if len(margs) is not 2:
            await self.bot.say("No roster name specified")
        elif len(margs[1]) > 99:
            await self.bot.say("Roster name too long")
        elif self.intable(c, message.server.id, margs[1]):
        # if margs[1] in self.rosters:
            await self.bot.say(margs[1] + ' already exists')
        else:
            self.newroster(conn, c, message.server.id, margs[1], message.author.id)
            # self.rosters[margs[1]] = []
            await self.bot.say('Created new roster called ' + margs[1] + 
                    '. Type >jr ' + margs[1] + ' to join')
        
        self.dbclose(conn)

    @commands.command(aliases=["jr"], pass_context=True, no_pm=True)
    async def joinroster(self, ctx):
        """Joins an existing roster

        Usage:
        joinroster <roster name>
        """
        t = self.setvars(ctx)
        message, margs, conn, c = t
        if len(margs) is not 2:
            await self.bot.say("No roster name specified. To see list of rosters, use the rosterstatus (rs) command")
        elif len(margs[1]) > 99:
            await self.bot.say("Roster name too long")
        elif not self.intable(c, message.server.id, margs[1]):
            await self.bot.say(margs[1] + " does not exist")
        else:
            try:
                self.addattendee(conn, c, message.server.id, margs[1], message.author.id)
                await self.bot.say('Added ' + 
                    message.author.display_name + ' to ' + margs[1])
            except DatabaseError:
                await self.bot.say(message.author.display_name +
                        ' already in roster ' + margs[1])
        self.dbclose(conn)

    @commands.command(aliases=["ur"], pass_context=True, no_pm=True)
    async def unroster(self, ctx):
        """Unrosters from an existing roster

        Usage:
        unroster <roster name>
        """
        t = self.setvars(ctx)
        message, margs, conn, c = t
        if len(margs) is not 2:
            await self.bot.say("No roster name specified. To see list of rosters, use the rosterstatus (rs) command")
        elif len(margs[1]) > 99:
            await self.bot.say("Roster name too long")
        elif not self.intable(c, message.server.id, margs[1]):
            await self.bot.say(margs[1] + " does not exist")
        else:
            if not self.inattendees(c, message.server.id, margs[1], message.author.id):
                await self.bot.say(message.author.display_name + ' not in roster ' +
                        margs[1])
            else:
                self.removeattendee(conn, c, message.server.id, margs[1], message.author.id)
                await self.bot.say('Removed ' + message.author.display_name +
                    ' from ' + margs[1])
        self.dbclose(conn)

    @commands.command(aliases=["dr"], pass_context=True, no_pm=True)
    async def delroster(self, ctx):
        """Deletes an existing roster. Only the roster author can delete(TODO)

        Usage:
        delroster <roster name>
        """
        t = self.setvars(ctx)
        message, margs, conn, c = t
        
        if len(margs) is not 2:
            await self.bot.say("No roster name specified")
        elif len(margs[1]) > 99:
            await self.bot.say("Roster name too long")
        elif not self.intable(c, message.server.id, margs[1]):
            await self.bot.say(margs[1] + " does not exist")
        else:
            self.del_db_roster(conn, c, message.server.id, margs[1])
            await self.bot.say(margs[1] + " deleted")
        self.dbclose(conn)

    @commands.command(aliases=["rs", "lr"], pass_context=True, no_pm=True)
    async def rosterstatus(self, ctx):
        """Displays members of a roster, or all rosters and member counts

        Usage:
        rosterstatus
        rosterstatus <roster name>
        """
        t = self.setvars(ctx)
        message, margs, conn, c = t
        
        if len(margs) is 1:
            # Display all rosters and their respective attendee counts
            r = self.rosterdetail(c, message.server.id)
            em = discord.Embed()
            title_elements = ["There are ", str(r['r_count']), " rosters"]
            em.title = "".join(title_elements)
            em.set_footer(text = "Rosterize by Xenocidel b20171015")
            desc_elements = []
            for rname, a_count in r['r_list'].items():
                desc_elements.append("(")
                desc_elements.append(rname)
                desc_elements.append(": ")
                desc_elements.append(str(a_count))
                desc_elements.append(") ")
            em.description = "".join(desc_elements)
            await self.bot.say(embed = em)
            
        elif len(margs) is 2:
            # Display roster author, attendee count, and attendees
            if len(margs[1]) > 99:
                await self.bot.say("Roster name too long")
            elif not self.intable(c, message.server.id, margs[1]):
                await self.bot.say(margs[1] + " does not exist")
            else:
                r = self.rosterdetail(c, message.server.id, margs[1])
                em = discord.Embed()
                title_elements = ["Roster status of ", margs[1], " (",
                        str(r['a_count']), " enrolled)"]
                em.title = "".join(title_elements) 
                em.set_footer(text = "Roster created by " +
                        message.server.get_member(r['author']).name)
                desc_elements = []
                for user in r['a_list']:
                    desc_elements.append(message.server.get_member(user).name)
                    desc_elements.append(' ')
                em.description = "".join(desc_elements)
                await self.bot.say(embed = em)
        self.dbclose(conn)

def setup(bot):
    n = Rosterize(bot)
    #bot.add_listener(n.check_poll_votes, "on_message")
    bot.add_cog(n)
