SOURCES = [
    {
        "name": "South Australia Tourism Commission",
        "url": "https://southaustralia.com/destinations/adelaide/what-s-on"
    },
    {
        "name": "Experience Adelaide",
        "url": "https://www.experienceadelaide.com.au/visit/whats-on/"
    },
    {
        "name": "Adelaide Oval",
        "url": "https://www.adelaideoval.com.au/whats-on/"
    },
    {
        "name": "Adelaide Convention Centre",
        "url": "https://www.adelaidecc.com.au/events/"
    },
    {
        "name": "Adelaide Festival Centre",
        "url": "https://www.adelaidefestivalcentre.com.au/whats-on"
    },
    {
        "name": "Hindley St Music Hall",
        "url": "https://www.hindleymusichall.com.au/"
    },
    {
        "name": "Adelaide Entertainment Centre",
        "url": "https://www.adelaideentertainmentcentre.com.au/events/"
    },
    {
        "name": "Coopers Stadium",
        "url": "https://www.coopersstadium.com.au/events/"
    },
    {
        "name": "Thebarton Theatre",
        "url": "https://thebartontheatre.com.au/"
    },
    {
        "name": "The Drive",
        "url": "https://www.thedriveadelaide.com.au/events/"
    },
    {
        "name": "Adelaide Symphony Orchestra",
        "url": "https://www.aso.com.au/concerts-tickets/whats-on/"
    },
    {
        "name": "Lion Arts Factory",
        "url": "https://lionartsfactory.com.au/whats-on/"
    },
    {
        "name": "Nineteen Ten",
        "url": "https://www.nineteenten.com.au/whats-on"
    },
    {
        "name": "Immersive Light and Art",
        "url": "https://immersivelightandart.com.au/whats-on/"
    },
    {
        "name": "State Opera South Australia",
        "url": "https://www.stateopera.com.au/productions"
    },
    {
        "name": "Adelaide Town Hall",
        "url": "https://www.adelaidetownhall.com.au/whats-on/"
    },
    {
        "name": "Nexus Arts",
        "url": "https://nexusarts.org.au/whats-on/"
    },
    {
        "name": "Dom Polski Centre",
        "url": "https://dompolskicentre.org.au/whats-on/"
    },
    {
        "name": "Kings of Comedy",
        "url": "https://koc.lol/comedy-club-adelaide/"
    },
    {
        "name": "Adelaide Repertory Theatre",
        "url": "https://adelaiderep.com/"
    },
    {
        "name": "State Theatre Company South Australia",
        "url": "https://statetheatrecompany.com.au/shows/"
    },
    {
        "name": "South Australian Museum",
        "url": "https://whatson.samuseum.sa.gov.au/"
    },
    {
        "name": "Art Gallery of South Australia",
        "url": "https://www.agsa.sa.gov.au/whats-on/event-calendar/"
    },
    {
        "name": "Adelaide Botanic Gardens",
        "url": "https://www.botanicgardens.sa.gov.au/whats-on"
    },
    {
        "name": "Adelaide Cemetery Tours",
        "url": "https://www.tours.aca.sa.gov.au/"
    },
    {
        "name": "ACE Gallery",
        "url": "https://www.ace.gallery/whats-on/exhibitions"
    },
    {
        "name": "Adelaide Central Market",
        "url": "https://adelaidecentralmarket.com.au/whats-on/"
    },
    {
        "name": "David Roche Foundation",
        "url": "https://www.rochegallery.com.au/exhibitions/"
    },
    {
        "name": "The Gov",
        "url": "https://www.thegov.com.au/"
    },
    {
        "name": "Norwood Concert Hall",
        "url": "https://www.norwoodconcerthall.com.au/events"
    },
    {
        "name": "Trinity Sessions",
        "url": "https://www.trinitysessions.org/"
    },
    {
        "name": "Morphettville Racecourse",
        "url": "https://morphettville.com.au/"
    },
    {
        "name": "Gilles at the Grounds",
        "url": "https://gillesatthegrounds.com.au/"
    },
    {
        "name": "Holden Street Theatres",
        "url": "https://www.holdenstreettheatres.com/"
    },
    {
        "name": "Baroque Hall",
        "url": "https://www.baroquehall.com/recitals"
    },
    {
        "name": "UniBar Adelaide",
        "url": "https://www.unibaradl.com.au/"
    },
    {
        "name": "Arkaba Hotel",
        "url": "https://www.arkabahotel.com.au/whats-on/"
    },
    {
        "name": "Rhino Room",
        "url": "https://rhinoroom.com.au/gig-guide/"
    },
    {
        "name": "Jive",
        "url": "https://www.jivevenue.com/whats-on"
    },
    {
        "name": "National Trust SA",
        "url": "https://www.nationaltrust.org.au/explore/?content=event&state=sa"
    },
    {
        "name": "MOD.",
        "url": "https://mod.org.au/"
    },
    {
        "name": "SAMSTAG Museum",
        "url": "https://unisa.edu.au/connect/samstag-museum/"
    },
    {
        "name": "Kerry Packer Civic Gallery",
        "url": "https://unisa.edu.au/connect/hawke-centre/kerry-packer-civic-gallery/"
    }
]
# Ticketmaster Adelaide listings (requires TICKETMASTER_API_KEY environment variable)
SOURCES.append({"name": "Ticketmaster Adelaide", "url": "https://app.ticketmaster.com/discovery/v2/events.json"})

# Regional AllEvents discovery, including Bonython Park.
SOURCES.append({"name": "AllEvents Adelaide and Surrounds", "url": "https://allevents.in/adelaide"})

# Government House public visitor activities.
SOURCES.append({"name": "Government House", "url": "https://www.governor.sa.gov.au/vice-regal/lunch-on-the-lawns"})

# Fever official Adelaide Candlelight concert catalogue
SOURCES.append({"name": "Fever Candlelight Adelaide", "url": "https://feverup.com/en/adelaide/candlelight"})

# Official outdoor concert promoter — SA events only.
SOURCES.append({"name": "A Day on the Green", "url": "https://www.adayonthegreen.com.au/"})

# Official Adelaide Zoo event listings.
SOURCES.append({"name": "Adelaide Zoo", "url": "https://www.adelaidezoo.com.au/events/"})

# Official National Wine Centre event listings.
SOURCES.append({"name": "National Wine Centre", "url": "https://www.nationalwinecentre.com.au/whats-on"})

# Adelaide Fringe official program. Individual shows appear as published.
SOURCES.append({"name": "Adelaide Fringe", "url": "https://adelaidefringe.com.au/fringetix/sessions"})

# Official Adelaide Festival program (distinct from Adelaide Festival Centre).
SOURCES.append({"name": "Adelaide Festival", "url": "https://www.adelaidefestival.com.au/whats-on"})

# Illuminate Adelaide official program; only dated events are published.
SOURCES.append({"name": "Illuminate Adelaide", "url": "https://www.illuminateadelaide.com/"})

# Individual film screenings only; no inferred season-wide sessions.
SOURCES.append({"name": "Moonlight Cinema Adelaide", "url": "https://adelaide.moonlight.com.au/program"})

# Official Adelaide Gaol special events; exclude routine admission and tours.
SOURCES.append({"name": "Adelaide Gaol", "url": "https://www.adelaidegaol.sa.gov.au/"})

# Play & Go is an independent event guide, not an official venue authority.
SOURCES.append({"name": "Play & Go Adelaide Major Events", "url": "https://playandgo.com.au/category/major-events/"})

# AMOSA official news and event pages: dated public events only.
SOURCES.append({"name": "Army Museum of South Australia", "url": "https://www.amosa.org.au/stories-and-events/what-s-happening"})

# Migration Museum: only verified future scheduled events (including off-site).
SOURCES.append({"name": "Migration Museum Adelaide", "url": "https://migration.history.sa.gov.au/what-is-on/"})

# Maritime Museum: verified scheduled public events and dated special tours.
SOURCES.append({"name": "South Australian Maritime Museum", "url": "https://maritime.history.sa.gov.au/what-is-on/"})

# SAAM: public special-event announcements, not daily museum admission.
SOURCES.append({"name": "South Australian Aviation Museum", "url": "https://saam.org.au/"})

# NRM: confirmed special events only; ordinary museum visits are excluded.
SOURCES.append({"name": "National Railway Museum", "url": "https://nrm.org.au/"})

# SALA Festival official ArtFuel exhibition and event program.
SOURCES.append({"name": "SALA Festival", "url": "https://www.salafestival.com/artfuel/program"})
