import discord, os, re, asyncio, pprint
from dotenv import load_dotenv
from discord.ext import commands, tasks
from urllib.request import urlopen, Request, HTTPError, urlretrieve
from bs4 import BeautifulSoup as bSoup

pp = pprint.PrettyPrinter(indent=4)

load_dotenv()
QC_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

help_command = commands.DefaultHelpCommand(
    no_category = 'Sheit Bot Commands'
)

bot = commands.Bot(
    command_prefix = "/sheit ",
    description = "SheitBot, a Netflix (un)original Bot which doesn't really need to exist.",
    help_command = help_command,
    case_insensitive=True
)

filmNamePattern = re.compile('^"(.+)".*:')

@bot.event
async def on_ready():
    print(f"{bot.user} connected to Discord.")

@bot.event
async def on_command_error(context, error):
    if isinstance(error, commands.MissingRequiredArgument):
        if (context.command.name == "find"):
            await context.send(f"\"{bot.command_prefix}{context.command}\" needs a film name to search.")
            return

    if (context.command.name == "general"):
        if isinstance(error, discord.NotFound):
            await context.send("Couldn't find General drinking game rules.")
            return

@bot.command(name="find", help="Find the rules for a particular film")
async def find(context, filmName):
    channel = context.channel
    messages = await getMessages(context)
    filmMatches = dict()
    
    for message in messages:
        match = filmNamePattern.match(message.content)

        if (match):
            filmNameFromMatch = match.group(1).lower()

            if (filmName.lower() in filmNameFromMatch):
                filmMatches[filmNameFromMatch] = message.content
                print(f"Match found for \"{filmName}\": {filmNameFromMatch}")
    
    if filmMatches:
        rulesFoundMessage = f"Rules found for {filmName}:\n\n"
        rulesFoundMessage += addSeparatingDashes(50)
        for film in filmMatches:
            rulesFoundMessage += f"{filmMatches[film]}\n"
            rulesFoundMessage += addSeparatingDashes(50)

        await context.send(rulesFoundMessage)
    else:
        await context.send(f"No rules found for \"{filmName}\"")

@bot.command(name="list", help="List all the films that rules have been posted for")
async def list_(context):
    messages = await getMessages(context)
    filmMatches = []

    for message in messages:
        match = filmNamePattern.match(message.content)

        if (match):
            filmNameFromMatch = match.group(1).lower()

            if filmNameFromMatch not in filmMatches:
                filmMatches.append(filmNameFromMatch)
    
    if filmMatches:
        numFilmMatches = len(filmMatches)
        print(f"Num Films found: {numFilmMatches}")
        filmMatches.sort()

        rulesFoundMessage = f"{numFilmMatches} Films have rules posted:\n\n"
        rulesFoundMessage += addSeparatingDashes(50)
        for film in filmMatches:
            rulesFoundMessage += f"{film.title()}\n"
        rulesFoundMessage += addSeparatingDashes(50)

        await context.send(rulesFoundMessage)
    else:
        await context.send("No valid film rules posted in this channel")

@bot.command(name="general", help="Show the General drinking game rules")
async def general(context):
    # NOTE: If the message for the general rules ever gets reposted, THIS HAS TO BE CHANGED.
    generalRulesMessageID = 718955666064277665
    generalRules = await findSpecificMessage(context, generalRulesMessageID)
    
    if generalRules:
        await context.send(generalRules)


@bot.command(name="ryan", help="Show Ryan's personal drinking game rules")
async def ryan(context):
    ryanRulesMessageID = 812120231182860356
    ryanRules = await findSpecificMessage(context, ryanRulesMessageID)
    
    if ryanRules:
        await context.send(ryanRules)

@bot.command(name="mark", help="Show Mark's personal drinking game rules")
async def mark(context):
    markRulesMessageID = 812120316708782121
    markRules = await findSpecificMessage(context, markRulesMessageID)
    
    if markRules:
        await context.send(markRules)

@bot.command(name="claudia", help="Show Claudia's personal drinking game rules")
async def claudia(context):
    claudiaRulesMessageID = 846899227137409044
    claudiaRules = await findSpecificMessage(context, claudiaRulesMessageID)
    
    if claudiaRules:
        await context.send(claudiaRules)

# Scrape justwatch.com/uk to find where films are hosted
@bot.command(name="whereToWatch", help="Find where to watch a certain film")
async def whereToWatch(context, filmName):
    print(f"Finding where to watch {filmName}")
    filmResults = await findFilm(context, filmName)
    print("Done")

    filmResultsMessage = addSeparatingDashes(50)
    filmResultsMessage += filmResults + "\n"
    filmResultsMessage += addSeparatingDashes(50)

    await context.send(filmResultsMessage)

async def findFilm(context, filmName):
    filmURL = filmName.replace(" ", "%20")
    baseUrl = "https://reelgood.com/"
    searchUrl = baseUrl + "search?q=" + filmURL
    print(f"url: {searchUrl}")
    filmSearchPage = getPage(searchUrl)
    filmDict = {}

    if (filmSearchPage):
        matchingFilms = filmSearchPage.findAll("div", {"class":"e1qyeclq5"})

        for i in range(0, len(matchingFilms)):
            film = matchingFilms[i]
            filmDict[i+1] = {
                "Name": film.a.find("span", {"class":"e1qyeclq4"}).text,
                "Url": film.a["href"]
            }

        chooseWhichFilmString = addSeparatingDashes(50)
        chooseWhichFilmString += "Which film do you want to check?\n"
        chooseWhichFilmString += addSeparatingDashes(50)
        for filmId in filmDict:
            chooseWhichFilmString += f"{filmId} | {filmDict[filmId]['Name']}\n"
        chooseWhichFilmString += addSeparatingDashes(50)

        print(chooseWhichFilmString)
        await context.send(chooseWhichFilmString)

        def check(msg):
            return msg.content.isnumeric()

        try:
            filmIdResponse = await bot.wait_for('message', timeout=10, check=check)
        except asyncio.TimeoutError:
            await context.send("Response wasn't received in time.")
            return
        
        chosenFilmString = ""
        chosenId = int(filmIdResponse.content)
        if (chosenId <= len(filmDict)):
            chosenFilmString = f"You chose: {filmDict[chosenId]['Name']}"
            chosenFilmString += f"\nGoing to {filmDict[chosenId]['Url']}"
        else:
            chosenFilmString = "You didn't enter a valid ID"
            return

        filmUrl = baseUrl + filmDict[chosenId]['Url']
        filmResultPage = getPage(filmUrl)

        allWatchingOptions = filmResultPage.findAll("div", {"class":"css-r5iejs e126mwsw1"})
        filmStreamingOptions = addSeparatingDashes(50)
        filmStreamingOptions += "Where to watch \'" + filmDict[chosenId]['Name'] + "\'\n"
        filmStreamingOptions += addSeparatingDashes(30)
        numStreamingSites = 0

        for option in allWatchingOptions:
            if "stream" in option["title"].lower():
                filmStreamingOptions += option.find("span", {"class":"e1udhou113"}).text + "\n"
                numStreamingSites += 1
        
        if numStreamingSites <= 0:
            filmStreamingOptions = addSeparatingDashes(50)
            filmStreamingOptions += "No sites found to stream\n"

        filmStreamingOptions += addSeparatingDashes(50)

        await context.send(filmStreamingOptions)

def getPage(url):
    print("Start of getPage")
    hdr = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'} 
    req = Request(url=url, headers=hdr)
    try:
        response = urlopen(req)
    except HTTPError:
        return None

    print("urlopened")

    # with open("pageOutput.html", mode="wb") as d:
    #     d.write(response.read())

    pageHTML = response.read() 
    page = bSoup(pageHTML, "html.parser")
    print("beautifulsoupified")

    return page

async def findSpecificMessage(context, id):
    message = await context.fetch_message(id)

    if (message):
        print(f"Found message with ID {id}")
        messageToSend = addSeparatingDashes(50)
        messageToSend += message.content + "\n"
        messageToSend += addSeparatingDashes(50)

        return messageToSend
    else:
        print(f"Couldn't find message with ID {id}")

async def getMessages(context):
    messages = await context.channel.history(oldest_first=True, limit=None).flatten()
    print(f"Num Messages found: {len(messages)}")
    return messages

def addSeparatingDashes(numDashes):
    string = ""
    for i in range(numDashes):
        string += "-"

    string += "\n"
    return string

bot.run(QC_TOKEN)