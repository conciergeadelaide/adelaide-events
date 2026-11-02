
"use strict";

// ======================================
// ADELAIDE EVENTS — CONCIERGE
// Complete script.js
// ======================================

var events = [];
var historicalEvents = [];
var pastEventsOnlyInput = document.getElementById("past-events-only");
var filteredEventsForCalendar = [];
var currentView = "cards";
var visibleMonth = new Date(
    new Date().getFullYear(),
    new Date().getMonth(),
    1
);
var selectedDay = "";

var eventsContainer = document.getElementById("events");
var searchInput = document.getElementById("search");
var dateFromInput = document.getElementById("date-from");
var dateToInput = document.getElementById("date-to");
var categoryFilter = document.getElementById("category-filter");
var categoryOptions = document.getElementById("category-options");
var categoryMultiselect = document.getElementById("category-multiselect");
var selectedCategories = [];
var venueFilter = document.getElementById("venue-filter");
var venueMultiselect = document.getElementById("venue-multiselect");
var venueOptions = document.getElementById("venue-options");
var venueSearch = document.getElementById("venue-search");
var venueCheckboxes = document.getElementById("venue-checkboxes");
var venueNoResults = document.getElementById("venue-no-results");
var selectedVenues = [];
var festivalFilter = document.getElementById("festival-filter");
var festivalOptions = document.getElementById("festival-options");
var festivalMultiselect = document.getElementById("festival-multiselect");
var selectedFestivals = [];

function getEventFestivals(event) {
    var festivals = Array.isArray(event.festival)
        ? event.festival.filter(Boolean).slice()
        : (typeof event.festival === "string" && event.festival ? [event.festival] : []);

    // Treat the orchestra as a Festival-filter grouping, not a venue.
    // This is derived from the source, so future scraped events work too.
    if (isAdelaideSymphonyEvent(event) &&
        festivals.indexOf("Adelaide Symphony Orchestra") === -1) {
        festivals.push("Adelaide Symphony Orchestra");
    }

    // Adelaide Festival is distinct from Adelaide Festival Centre.
    // Include only events whose source is exactly Adelaide Festival.
    if (String(event.source || event.source_name || "").trim().toLowerCase() === "adelaide festival" &&
        festivals.indexOf("Adelaide Festival") === -1) {
        festivals.push("Adelaide Festival");
    }
    return festivals;
}

function updateFestivalLabel() {
    festivalFilter.textContent = selectedFestivals.length === 0
        ? "All festivals"
        : selectedFestivals.length === 1
            ? selectedFestivals[0]
            : selectedFestivals.length + " festivals selected";
}

function closeFestivalOptions() {
    festivalOptions.classList.add("hidden");
    festivalFilter.setAttribute("aria-expanded", "false");
}

var sortSelect = document.getElementById("sort");
var hideLongEventsInput = document.getElementById("hide-long-events");
var eventCount = document.getElementById("event-count");
var noResults = document.getElementById("no-results");
var clearFiltersButton = document.getElementById("clear-filters");

// ======================================
// DATE HELPERS
// ======================================

function getEventStart(event) {
    return event.datetime || event.date || "";
}

function getEventEnd(event) {
    return event.end_datetime ||
           event.end_date ||
           getEventStart(event);
}

function getDatePart(value) {
    if (!value) return "";

    var match = String(value).match(
        /^(\d{4}-\d{2}-\d{2})/
    );

    return match ? match[1] : "";
}

function parseLocalDate(value) {
    var datePart = getDatePart(value);

    if (!datePart) return null;

    var parts = datePart.split("-");
    var year = Number(parts[0]);
    var month = Number(parts[1]);
    var day = Number(parts[2]);

    var date = new Date(
        year,
        month - 1,
        day,
        12,
        0,
        0
    );

    if (
        isNaN(date.getTime()) ||
        date.getFullYear() !== year ||
        date.getMonth() !== month - 1 ||
        date.getDate() !== day
    ) {
        return null;
    }

    return date;
}

function getEventTimestamp(event) {
    var value = getEventStart(event);

    if (!value) {
        return Number.MAX_SAFE_INTEGER;
    }

    var date = new Date(value);

    if (isNaN(date.getTime())) {
        return Number.MAX_SAFE_INTEGER;
    }

    return date.getTime();
}

function formatDate(value) {
    if (!value) {
        return "Date to be confirmed";
    }

    var date = parseLocalDate(value);

    if (!date) {
        return "Date to be confirmed";
    }

    var dateText = new Intl.DateTimeFormat(
        "en-AU",
        {
            weekday: "short",
            day: "numeric",
            month: "short",
            year: "numeric"
        }
    ).format(date);

    var timeMatch = String(value).match(
        /T(\d{2}):(\d{2})/
    );

    if (!timeMatch) {
        return dateText;
    }

    var hours = Number(timeMatch[1]);
    var minutes = Number(timeMatch[2]);

    if (hours === 0 && minutes === 0) {
        return dateText;
    }

    var timeDate = new Date(
        date.getFullYear(),
        date.getMonth(),
        date.getDate(),
        hours,
        minutes
    );

    var timeText = new Intl.DateTimeFormat(
        "en-AU",
        {
            hour: "numeric",
            minute: "2-digit"
        }
    ).format(timeDate);

    return dateText + " · " + timeText;
}

function formatEventDate(event) {
    var startValue = getEventStart(event);
    var endValue = getEventEnd(event);

    var startDate = parseLocalDate(startValue);
    var endDate = parseLocalDate(endValue);

    if (!startDate) {
        return "Date to be confirmed";
    }

    if (
        !endDate ||
        endDate.getTime() <= startDate.getTime()
    ) {
        return formatDate(startValue);
    }

    var sameYear =
        startDate.getFullYear() ===
        endDate.getFullYear();

    var sameMonth =
        sameYear &&
        startDate.getMonth() === endDate.getMonth();

    var startDay = startDate.getDate();
    var endDay = endDate.getDate();

    var startMonth = new Intl.DateTimeFormat(
        "en-AU",
        { month: "short" }
    ).format(startDate);

    var endMonth = new Intl.DateTimeFormat(
        "en-AU",
        { month: "short" }
    ).format(endDate);

    var startYear = startDate.getFullYear();
    var endYear = endDate.getFullYear();

    if (sameMonth) {
        return (
            startDay + "–" + endDay +
            " " + startMonth + " " + startYear
        );
    }

    if (sameYear) {
        return (
            startDay + " " + startMonth +
            " – " +
            endDay + " " + endMonth +
            " " + endYear
        );
    }

    return (
        startDay + " " + startMonth +
        " " + startYear +
        " – " +
        endDay + " " + endMonth +
        " " + endYear
    );
}

// ======================================
// EVENT DURATION FILTER
// ======================================

// Counts calendar days inclusively.
//
// Examples:
// 1–7 October = 7 days: show
// 1–8 October = 8 days: hide
//
// Missing or invalid end dates are shown.
//
// UTC date arithmetic avoids daylight-saving
// changes affecting the duration calculation.

function isEventLongerThanSevenDays(event) {
    var startString = getDatePart(
        getEventStart(event)
    );

    var endString = getDatePart(
        event.end_datetime || event.end_date || ""
    );

    if (!startString || !endString) {
        return false;
    }

    var startDate = parseLocalDate(startString);
    var endDate = parseLocalDate(endString);

    if (!startDate || !endDate) {
        return false;
    }

    if (endDate <= startDate) {
        return false;
    }

    var startUTC = Date.UTC(
        startDate.getFullYear(),
        startDate.getMonth(),
        startDate.getDate()
    );

    var endUTC = Date.UTC(
        endDate.getFullYear(),
        endDate.getMonth(),
        endDate.getDate()
    );

    var durationDays =
        (endUTC - startUTC) / 86400000 + 1;

    return durationDays > 7;
}

// ======================================
// CATEGORY HELPERS
// ======================================

function normaliseEventCategory(category) {
    var name = String(category || "").trim();
    if (/^exhibitions?$/i.test(name)) return "Exhibition";
    if (/^talks(?:\s*&\s*conferences)?$/i.test(name)) return "Talks & Conferences";
    return name;
}

function getEventCategories(event) {
    var raw = Array.isArray(event.category)
        ? event.category
        : (event.category ? [event.category] : []);
    var categories = [];
    raw.forEach(function(category) {
        var name = normaliseEventCategory(category);
        if (name && categories.indexOf(name) === -1) categories.push(name);
    });
    return categories.length ? categories : ["Other"];
}

function getCategoryText(event) {
    return getEventCategories(event).join(" · ");
}

// Calendar colour palette. The first category determines an event's colour.
var CALENDAR_CATEGORY_COLOURS = {
    "Arts & Culture": "#7655A5",
    "Comedy": "#A75B12",
    "Community": "#527D2C",
    "Expos": "#5465A8",
    "Exhibition": "#5465A8",
    "Family": "#087F87",
    "Festival": "#B83F69",
    "Food & Beverage": "#9C5A27",
    "Music": "#245EAE",
    "Other": "#596674",
    "Sport": "#177A4C",
    "Talks & Conferences": "#65549A",
    "Theatre": "#793CB0",
    "Workshop": "#826324",
    "Club / Party": "#A83388",
    "Club/Party": "#A83388"
};

function calendarCategory(event) {
    var categories = getEventCategories(event);
    for (var i = 0; i < categories.length; i++) {
        if (Object.prototype.hasOwnProperty.call(CALENDAR_CATEGORY_COLOURS, categories[i])) {
            return categories[i];
        }
    }
    return "Other";
}

function calendarCategoryColour(event) {
    return CALENDAR_CATEGORY_COLOURS[calendarCategory(event)];
}

function renderCalendarLegend() {
    var legend = document.getElementById("calendar-category-legend");
    if (!legend) return;
    legend.replaceChildren();
    Object.keys(CALENDAR_CATEGORY_COLOURS).forEach(function(category) {
        if (category === "Club/Party") return;
        var item = document.createElement("span");
        item.className = "calendar-legend-item";
        var swatch = document.createElement("span");
        swatch.className = "calendar-legend-swatch";
        swatch.style.backgroundColor = CALENDAR_CATEGORY_COLOURS[category];
        swatch.setAttribute("aria-hidden", "true");
        var label = document.createElement("span");
        label.textContent = category;
        item.append(swatch, label);
        legend.appendChild(item);
    });
}

// ======================================
// STANDARDISE VENUE NAMES
// ======================================

function canonicalVenue(value) {
    var name = String(value || "").trim();

    if (/^the ed castle(?: hotel)?$/i.test(name)) {
        return "The Ed Castle";
    }
    if (/^(?:div-de|divide(?:,\s*adelaide)?)$/i.test(name)) {
        return "DIV-DE";
    }
    if (/^hindley (?:st|street) music hall$/i.test(name)) {
        return "Hindley Street Music Hall";
    }
    if (/^various venues accross south australia$/i.test(name) ||
        /^various venues across south australia$/i.test(name)) {
        return "Various";
    }
    var aliases = {
        "adelaide showground - old brick dairy": "Adelaide Showground",
        "adelaide showground": "Adelaide Showground",
        "botanic park": "Botanic Park / Tainmuntilla",
        "botanic park / tainmuntilla": "Botanic Park / Tainmuntilla",
        "elder park, adelaide": "Elder Park",
        "elder park": "Elder Park",
        "festival plaza, adelaide": "Festival Plaza",
        "festival plaza": "Festival Plaza",
        "ila | immersive light and art": "Immersive Light and Art (ILA)",
        "immersive light and art (ila)": "Immersive Light and Art (ILA)",
        "mclaren vale institute hall": "McLaren Vale Institute Hall",
        "mclaren vale institute hall": "McLaren Vale Institute Hall",
        "national wine centre of australia": "National Wine Centre",
        "national wine centre": "National Wine Centre",
        "rhino room, adelaide": "Rhino Room",
        "rhino room": "Rhino Room",
        "st peter's cathedral": "St Peter's Cathedral",
        "st peter's cathedral": "St Peter's Cathedral",
        "ukaria cultural centre": "UKARIA Cultural Centre",
        "ukaria cultural centre": "UKARIA Cultural Centre",
        "victoria square": "Victoria Square / Tarntanyangga",
        "victoria square / tartanyangga": "Victoria Square / Tarntanyangga",
        "victoria square / tarntanyangga": "Victoria Square / Tarntanyangga",
    };
    if (name.toLowerCase() === "family friendly events & shows") return "";
    return aliases[name.toLowerCase()] || name;
}

// Adelaide Symphony Orchestra is an organiser, not a physical venue.
// It is exposed in the Festival dropdown by getEventFestivals(), while
// retaining the actual performance location on each event card.
var ASO_FILTER_LABEL = "Adelaide Symphony Orchestra";

function isAdelaideSymphonyEvent(event) {
    var source = String(event.source || event.source_name || "")
        .trim().toLowerCase();
    var sourceUrl = String(event.source_url || "").toLowerCase();
    var eventUrl = String(event.link || event.url || "").toLowerCase();
    var organiser = String(event.organiser || event.organizer || "")
        .trim().toLowerCase();

    return source === "adelaide symphony orchestra" ||
        organiser === "adelaide symphony orchestra" ||
        /(?:^|\/)aso\.com\.au(?:\/|$)/.test(sourceUrl.replace(/^https?:\/\//, "")) ||
        /(?:^|\/)aso\.com\.au(?:\/|$)/.test(eventUrl.replace(/^https?:\/\//, ""));
}

function updateCategoryLabel() {
    categoryFilter.textContent = selectedCategories.length === 0
        ? "All categories"
        : selectedCategories.length === 1
            ? selectedCategories[0]
            : selectedCategories.length + " categories selected";
}

function closeCategoryOptions() {
    categoryOptions.classList.add("hidden");
    categoryFilter.setAttribute("aria-expanded", "false");
}

function updateVenueLabel() {
    venueFilter.textContent = selectedVenues.length === 0
        ? "All venues/locations"
        : selectedVenues.length === 1
            ? selectedVenues[0]
            : selectedVenues.length + " venues/locations selected";
}

function closeVenueOptions() {
    venueOptions.classList.add("hidden");
    venueFilter.setAttribute("aria-expanded", "false");
}

function filterVenueChoices() {
    var query = venueSearch.value.toLowerCase().trim();
    var visibleCount = 0;

    venueCheckboxes.querySelectorAll(".venue-option").forEach(function(option) {
        var venueName = option.dataset.venue || "";
        var checkbox = option.querySelector('input[type="checkbox"]');

        var matchesSearch = venueName.toLowerCase().includes(query);
        var isSelected = checkbox && checkbox.checked;

        var shouldShow = matchesSearch || isSelected;

        option.classList.toggle("hidden", !shouldShow);

        if (shouldShow) {
            visibleCount++;
        }
    });

    venueNoResults.classList.toggle("hidden", visibleCount > 0);
}
// ======================================
// VENUE HELPERS
// ======================================

// Only actual venue/building names should
// appear in the Venue dropdown.
//
// Addresses and generic locations remain
// available in event cards and search.

function isActualVenue(value) {
    if (typeof value !== "string") {
        return false;
    }

    var venue = value.trim();

    if (!venue) {
        return false;
    }

    var lower = venue.toLowerCase();
    if (lower === "family friendly events & shows") return false;

    var excludedLocations = [
        "mundy street",
        "north terrace",
        "north terrace, adjacent, morphett st bridge",
        "west beach road",
        "riverbank footbridge"
    ];

    if (excludedLocations.indexOf(lower) !== -1) {
        return false;
    }

    if (
        /^[a-z][a-z\s\x27-]*\s(?:street|road|avenue|terrace|lane|boulevard|highway|crescent|court)$/i.test(venue)
    ) {
        return false;
    }

    if (
        /\b(?:street|road|avenue|terrace|lane|boulevard|highway)\s*,\s*(?:adjacent|near|opposite|corner|at)\b/i.test(venue)
    ) {
        return false;
    }

    var genericLocations = [
        "adelaide",
        "adelaide cbd",
        "adelaide city",
        "south australia",
        "sa",
        "australia",
        "city of adelaide",
        "adelaide sa",
        "adelaide south australia",
        "various locations",
        "various venues",
        "multiple locations",
        "multiple venues",
        "tba",
        "tbc",
        "to be confirmed",
        "location to be confirmed",
        "venue to be confirmed",
        "online"
    ];

    if (genericLocations.indexOf(lower) !== -1) {
        return false;
    }

    if (/\b(?:SA\s*)?\d{4}\b/i.test(venue)) {
        return false;
    }

    if (
        /^\s*\d+[a-z]?(?:\s*[-\/]\s*\d+[a-z]?)?\s+/i.test(venue)
    ) {
        return false;
    }

    if (
        /^(?:unit|suite|level|floor|shop|lot|building)\s+\d+\b/i.test(venue)
    ) {
        return false;
    }

    var streetType =
        /\b(?:street|st|road|rd|avenue|ave|boulevard|blvd|terrace|tce|lane|ln|drive|dr|highway|hwy|parade|pde|place|pl|crescent|circuit|court|ct|way)\b/i;

    if (
        /\d/.test(venue) &&
        streetType.test(venue)
    ) {
        return false;
    }

    if (
        /^(?:corner|cnr)\s+(?:of\s+)?/i.test(venue)
    ) {
        return false;
    }

    if (
        /\b(?:corner of|intersection of|junction of)\b/i.test(venue)
    ) {
        return false;
    }

    if (
        streetType.test(venue) &&
        /,\s*(?:adelaide|north adelaide|south australia|sa)\b/i.test(venue)
    ) {
        return false;
    }

    if (
        /^-?\d{1,3}\.\d+[, ]+-?\d{1,3}\.\d+$/.test(venue)
    ) {
        return false;
    }

    if (
        /^(?:located at|address:|location:)\s*/i.test(venue)
    ) {
        return false;
    }

    return true;
}

// ======================================
// CREATE EVENT CARD
// ======================================

function createEventCard(event) {
    var article = document.createElement("article");
    article.className = "event-card";

    var imageContainer = document.createElement("div");
    imageContainer.className = "event-image";

    var image = document.createElement("img");

    if (event.image) {
        image.src = event.image;
    } else {
        image.src =
            "https://images.unsplash.com/photo-1492684223066-81342ee5ff30";
    }

    image.alt = event.title || "Adelaide event";
    image.loading = "lazy";

    // Show one individually coloured badge for every category.
    // Keep the original badge wrapper's position over the image.
    var badge = document.createElement("span");
    badge.className = "category-badge";
    badge.style.backgroundColor = "transparent";
    badge.style.padding = "0";
    badge.style.display = "flex";
    badge.style.flexWrap = "wrap";
    badge.style.gap = "5px";
    badge.style.maxWidth = "calc(100% - 24px)";

    getEventCategories(event).forEach(function(category) {
        var categoryBadge = document.createElement("span");
        categoryBadge.textContent = category;
        categoryBadge.style.backgroundColor =
            CALENDAR_CATEGORY_COLOURS[category] || CALENDAR_CATEGORY_COLOURS.Other;
        categoryBadge.style.color = "#ffffff";
        categoryBadge.style.padding = "6px 9px";
        categoryBadge.style.lineHeight = "1.3";
        categoryBadge.style.overflowWrap = "anywhere";
        badge.appendChild(categoryBadge);
    });

    imageContainer.appendChild(image);
    imageContainer.appendChild(badge);

    var content = document.createElement("div");
    content.className = "event-content";

    var date = document.createElement("div");
    date.className = "event-date";
    date.textContent = formatEventDate(event);

    var title = document.createElement("h3");
    title.className = "event-title";
    title.textContent =
        event.title || "Untitled Event";

    var venue = document.createElement("div");
    venue.className = "event-venue";

    var venueIcon = document.createElement("span");
    venueIcon.className = "venue-icon";
    venueIcon.textContent = "●";

    var venueText = document.createElement("span");

    var venueName = event.venue || "";
    var locationName = event.location || "";

    if (venueName && locationName) {
        if (
            venueName.trim().toLowerCase() ===
            locationName.trim().toLowerCase()
        ) {
            venueText.textContent = venueName;
        } else {
            venueText.textContent =
                venueName + " · " + locationName;
        }
    } else {
        venueText.textContent =
            venueName || locationName || "Adelaide";
    }

    venue.appendChild(venueIcon);
    venue.appendChild(venueText);

    var link = document.createElement("a");
    link.className = "event-link";

    link.href = event.link || event.url || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "View Event";

    content.appendChild(date);
    content.appendChild(title);
    content.appendChild(venue);
    content.appendChild(link);

    article.appendChild(imageContainer);
    article.appendChild(content);

    return article;
}

// ======================================
// DISPLAY EVENTS
// ======================================

function displayEvents(eventList) {
    eventsContainer.innerHTML = "";

    eventCount.textContent =
        eventList.length +
        " event" +
        (eventList.length === 1 ? "" : "s");

    if (eventList.length === 0) {
        noResults.classList.remove("hidden");
        return;
    }

    noResults.classList.add("hidden");

    eventList.forEach(function(event) {
        eventsContainer.appendChild(
            createEventCard(event)
        );
    });
}

// ======================================
// POPULATE FILTER DROPDOWNS
// ======================================

function populateFilters() {
    categoryOptions.replaceChildren();
    selectedCategories = [];
    updateCategoryLabel();

    venueCheckboxes.replaceChildren();
    selectedVenues = [];
    venueSearch.value = "";
    updateVenueLabel();

    var categories = [
        "Arts & Culture",
        "Comedy",
        "Community",
        "Expos",
        "Exhibition",
        "Family",
        "Festival",
        "Food & Beverage",
        "Music",
        "Other",
        "Sport",
        "Talks & Conferences",
        "Theatre",
        "Workshop"
    ];

    festivalOptions.replaceChildren();
    selectedFestivals = [];
    updateFestivalLabel();
    var festivals = Array.from(new Set(events.flatMap(getEventFestivals))).sort(
        function(a, b) { return a.localeCompare(b); }
    );
    festivals.forEach(function(festival) {
        var option = document.createElement("label");
        option.className = "festival-option";
        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = festival;
        var text = document.createElement("span");
        text.textContent = festival;
        checkbox.addEventListener("change", function() {
            if (checkbox.checked) {
                if (!selectedFestivals.includes(festival)) selectedFestivals.push(festival);
            } else {
                selectedFestivals = selectedFestivals.filter(function(x) { return x !== festival; });
            }
            updateFestivalLabel();
            applyFilters();
        });
        option.appendChild(checkbox);
        option.appendChild(text);
        festivalOptions.appendChild(option);
    });

    var venues = [];

    events.forEach(function(event) {
        getEventCategories(event).forEach(
            function(category) {
                if (
                    categories.indexOf(category) === -1
                ) {
                    categories.push(category);
                }
            }
        );

        if (
            event.venue &&
            isActualVenue(event.venue) &&
            event.venue.trim().toLowerCase() !== ASO_FILTER_LABEL.toLowerCase() &&
            venues.indexOf(event.venue) === -1
        ) {
            venues.push(event.venue);
        }
    });


    categories.sort(function(a, b) {
        return a.localeCompare(b);
    });

    venues.sort(function(a, b) {
        return a.localeCompare(b);
    });

    categories.forEach(function(category) {
        var option = document.createElement("label");
        option.className = "category-option";

        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = category;

        var text = document.createElement("span");
        text.textContent = category;

        checkbox.addEventListener("change", function() {
            if (checkbox.checked) {
                if (selectedCategories.indexOf(category) === -1) {
                    selectedCategories.push(category);
                }
            } else {
                selectedCategories = selectedCategories.filter(
                    function(value) {
                        return value !== category;
                    }
                );
            }

            updateCategoryLabel();
            applyFilters();
        });

        option.appendChild(checkbox);
        option.appendChild(text);
        categoryOptions.appendChild(option);
    });

    venues.forEach(function(venue) {
        var option = document.createElement("label");
        option.className = "venue-option";
        option.dataset.venue = venue;

        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = venue;

        var text = document.createElement("span");
        text.textContent = venue;

        checkbox.addEventListener("change", function() {
            if (checkbox.checked) {
                if (!selectedVenues.includes(venue)) selectedVenues.push(venue);
            } else {
                selectedVenues = selectedVenues.filter(function(value) {
                    return value !== venue;
                });
            }
            updateVenueLabel();
            applyFilters();
        });

        option.appendChild(checkbox);
        option.appendChild(text);
        venueCheckboxes.appendChild(option);
    });
    filterVenueChoices();

    console.log(
        "Venue dropdown:",
        venues.length,
        "venue names"
    );
}

// ======================================
// APPLY SEARCH AND FILTERS
// ======================================


// ======================================
// CONCIERGE: QUICK DATES / AGENDA / PRINT
// ======================================
var quickDateChoice = "";
var agendaContainer = document.getElementById("agenda-view");
var printGuideContainer = document.getElementById("print-guide-content");

function dateInputValue(date) {
    return dateKey(date.getFullYear(), date.getMonth(), date.getDate());
}
function shiftedDate(date, offset) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate() + offset, 12);
}
function setQuickDate(choice) {
    var now = new Date();
    var start = shiftedDate(now, 0);
    var end = start;
    if (choice === "all") {
        dateFromInput.value = "";
        dateToInput.value = "";
    } else {
        if (choice === "tomorrow") start = shiftedDate(now, 1);
        if (choice === "weekend") {
            // Australian weekend is Saturday and Sunday. On Sunday, include today.
            var weekday = now.getDay();
            var daysUntilSaturday = (6 - weekday + 7) % 7;
            if (weekday === 0) daysUntilSaturday = -1;
            start = shiftedDate(now, daysUntilSaturday);
            end = shiftedDate(start, 1);
        } else if (choice === "7" || choice === "30") {
            end = shiftedDate(start, Number(choice) - 1);
        } else {
            end = start;
        }
        dateFromInput.value = dateInputValue(start);
        dateToInput.value = dateInputValue(end);
        if (currentView === "calendar") {
            visibleMonth = new Date(start.getFullYear(), start.getMonth(), 1);
            selectedDay = "";
        }
    }
    quickDateChoice = choice;
    updateQuickDateButtons();
    applyFilters();
}
function updateQuickDateButtons() {
    document.querySelectorAll("[data-quick-date]").forEach(function(button) {
        var active = button.getAttribute("data-quick-date") === quickDateChoice;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
    });
}
document.querySelectorAll("[data-quick-date]").forEach(function(button) {
    button.addEventListener("click", function() {
        setQuickDate(button.getAttribute("data-quick-date"));
    });
});
function clearQuickDateSelection() {
    quickDateChoice = "";
    updateQuickDateButtons();
}
function eventTimeSort(a, b) {
    var ad = getDatePart(getEventStart(a));
    var bd = getDatePart(getEventStart(b));
    if (ad !== bd) return ad.localeCompare(bd);
    var at = calendarStartTime(a);
    var bt = calendarStartTime(b);
    if (at === null && bt !== null) return 1;
    if (bt === null && at !== null) return -1;
    if (at !== null && bt !== null && at !== bt) return at - bt;
    return String(a.title || "").localeCompare(String(b.title || ""));
}
function makeAgendaRow(event) {
    var row = document.createElement("article");
    row.className = "agenda-item";
    var time = document.createElement("span");
    time.className = "agenda-time";
    time.textContent = calendarTimeLabel(event);
    var body = document.createElement("div");
    body.className = "agenda-item-body";
    var title = document.createElement("strong");
    title.textContent = event.title || "Untitled Event";
    var info = document.createElement("p");
    info.textContent = (event.venue || event.location || "Venue TBC") + " · " + getEventCategories(event).join(", ");
    body.append(title, info);
    row.append(time, body);
    var url = event.link || event.url;
    if (url && /^https?:\/\//i.test(String(url))) {
        var link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Event details";
        link.className = "agenda-link";
        row.appendChild(link);
    }
    return row;
}
function renderAgenda(eventList) {
    agendaContainer.replaceChildren();
    if (currentView !== "agenda") return;
    var sorted = eventList.slice().sort(eventTimeSort);
    if (!sorted.length) {
        var empty = document.createElement("p");
        empty.className = "agenda-empty";
        empty.textContent = "No events match these filters.";
        agendaContainer.appendChild(empty);
        return;
    }
    var lastDate = "";
    sorted.forEach(function(event) {
        var day = getDatePart(getEventStart(event));
        if (day !== lastDate) {
            lastDate = day;
            var heading = document.createElement("h3");
            heading.className = "agenda-day-heading";
            heading.textContent = day ? formatDate(day) : "Date TBC";
            agendaContainer.appendChild(heading);
        }
        agendaContainer.appendChild(makeAgendaRow(event));
    });
}
function printCurrentGuide() {
    // Avoid accidentally printing hundreds of pages when no date is selected.
    var from = dateFromInput.value;
    var to = dateToInput.value;
    var today = dateInputValue(new Date());
    var printFrom = from || (to ? "" : today);
    var printTo = to || (from ? "" : today);
    var records = filteredEventsForCalendar.filter(function(event) {
        var start = getDatePart(getEventStart(event));
        var end = getDatePart(getEventEnd(event)) || start;
        return start && (!printFrom || end >= printFrom) && (!printTo || start <= printTo);
    }).slice().sort(eventTimeSort);
    printGuideContainer.replaceChildren();
    var heading = document.createElement("h1");
    heading.textContent = "CONCIERGE · What's On Adelaide";
    var sub = document.createElement("p");
    sub.textContent = "Events guide · " + (printFrom || "Any date") + " to " + (printTo || "Any date") + " · " + records.length + " events";
    printGuideContainer.append(heading, sub);
    if (!records.length) {
        var empty = document.createElement("p");
        empty.textContent = "No matching events.";
        printGuideContainer.appendChild(empty);
    }
    var lastDate = "";
    records.forEach(function(event) {
        var day = getDatePart(getEventStart(event));
        if (day !== lastDate) {
            lastDate = day;
            var dateHeading = document.createElement("h2");
            dateHeading.textContent = formatDate(day);
            printGuideContainer.appendChild(dateHeading);
        }
        var row = document.createElement("div");
        row.className = "print-guide-row";
        var main = document.createElement("strong");
        main.textContent = calendarTimeLabel(event) + "  ·  " + (event.title || "Untitled Event");
        var venue = document.createElement("p");
        venue.textContent = event.venue || event.location || "Venue TBC";
        row.append(main, venue);
        var url = event.link || event.url;
        if (url && /^https?:\/\//i.test(String(url))) {
            var link = document.createElement("a");
            link.href = url;
            link.textContent = "Event website";
            row.appendChild(link);
        }
        printGuideContainer.appendChild(row);
    });
    var note = document.createElement("p");
    note.className = "print-guide-note";
    note.textContent = "Event details may change. Please confirm times and availability with the organiser.";
    printGuideContainer.appendChild(note);
    window.print();
}
document.getElementById("print-guide").addEventListener("click", printCurrentGuide);
document.getElementById("view-agenda").addEventListener("click", function() { setView("agenda"); });

function applyFilters() {
    var searchText =
        searchInput.value.toLowerCase().trim();

    var dateFrom = dateFromInput.value;
    var dateTo = dateToInput.value;


    // Calendar always hides long-running events, regardless of prior Cards settings.
    var hideLongEvents = currentView === "calendar" || Boolean(
        hideLongEventsInput && hideLongEventsInput.checked
    );

    var todayKey = dateKey(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());
    var sourceEvents = pastEventsOnlyInput && pastEventsOnlyInput.checked ? historicalEvents : events;
    var filteredEvents = sourceEvents.filter(
        function(event) {
            var eventStartString = getDatePart(
                getEventStart(event)
            );

            var eventEndString = getDatePart(
                getEventEnd(event)
            ) || eventStartString;

            var isPast = Boolean(eventEndString && eventEndString < todayKey);
            if (pastEventsOnlyInput && pastEventsOnlyInput.checked ? !isPast : isPast) return false;

            var searchableText = (
                (event.title || "") +
                " " +
                (event.venue || "") +
                " " +
                (event.location || "") +
                " " +
                getCategoryText(event)
            ).toLowerCase();

            var matchesSearch =
                searchableText.indexOf(searchText) !== -1;

            // Include multi-day events if their
            // date range overlaps selected dates.

            var matchesFrom =
                !dateFrom ||
                (
                    eventEndString !== "" &&
                    eventEndString >= dateFrom
                );

            var matchesTo =
                !dateTo ||
                (
                    eventStartString !== "" &&
                    eventStartString <= dateTo
                );

            // Match ANY selected category.
            // No selections means all categories.

            var eventCategories =
                getEventCategories(event);

            var matchesCategory =
                selectedCategories.length === 0 ||
                selectedCategories.some(
                    function(category) {
                        return eventCategories.indexOf(
                            category
                        ) !== -1;
                    }
                );

            var matchesVenue =
                selectedVenues.length === 0 ||
                selectedVenues.includes(event.venue);

            var matchesFestival = selectedFestivals.length === 0 ||
                selectedFestivals.some(function(festival) {
                    return getEventFestivals(event).includes(festival);
                });

            var matchesDuration =
                !hideLongEvents ||
                !isEventLongerThanSevenDays(event);

            var matchesCalendarCategory =
                currentView !== "calendar" ||
                !isExcludedCalendarCategory(event);

            return (
                matchesSearch &&
                matchesFrom &&
                matchesTo &&
                matchesCategory &&
                matchesVenue &&
                matchesFestival &&
                matchesDuration &&
                matchesCalendarCategory
            );
        }
    );

    sortEvents(filteredEvents);
}

// ======================================
// SORT EVENTS
// ======================================

function sortEvents(eventList) {
    var sortMethod = sortSelect.value;

    eventList.sort(function(a, b) {
        if (sortMethod === "date-asc") {
            return (
                getEventTimestamp(a) -
                getEventTimestamp(b)
            );
        }

        if (sortMethod === "date-desc") {
            return (
                getEventTimestamp(b) -
                getEventTimestamp(a)
            );
        }

        if (sortMethod === "title") {
            return (a.title || "").localeCompare(
                b.title || ""
            );
        }

        if (sortMethod === "venue") {
            return (a.venue || "").localeCompare(
                b.venue || ""
            );
        }

        return 0;
    });

    filteredEventsForCalendar = eventList;

    if (currentView === "agenda") {
        eventCount.textContent = eventList.length + " events";
        renderAgenda(eventList);
    } else if (currentView === "calendar") {
        eventCount.textContent =
            eventList.length +
            " events";

        renderCalendar();
    } else {
        displayEvents(eventList);
    }
}

// ======================================
// MONTHLY CALENDAR
// ======================================

function dateKey(year, month, day) {
    return (
        year + "-" +
        String(month + 1).padStart(2, "0") +
        "-" +
        String(day).padStart(2, "0")
    );
}

// Calendar shows all eligible events, excluding long-running events
// and the categories listed below. Cards retains the full selection.
function isExcludedCalendarCategory(event) {
    return getEventCategories(event).some(function(category) {
        var value = normalizedCalendarText(category);
        return value === "exhibition" || value === "exhibitions" ||
            value === "workshop" || value === "workshops" ||
            value === "talks" || value === "conference" ||
            value === "conferences" || value === "talks & conferences";
    });
}

function normalizedCalendarText(value) {
    return String(value || "")
        .toLowerCase()
        .replace(/[’‘]/g, "'")
        .replace(/\s+/g, " ")
        .trim();
}

function calendarEventTitle(event) {
    return event.title || "Untitled Event";
}

function eventsForDay(key) {
    return filteredEventsForCalendar.filter(
        function(event) {
            var start = getDatePart(
                getEventStart(event)
            );

            var end = getDatePart(
                getEventEnd(event)
            ) || start;

            return Boolean(
                start &&
                start <= key &&
                end >= key
            );
        }
    );
}

function showDay(key) {
    selectedDay = key;

    renderCalendar();

    document.getElementById(
        "calendar-details"
    ).scrollIntoView({
        behavior: "smooth",
        block: "nearest"
    });
}

function calendarStartTime(event) {
    var value = String(getEventStart(event) || "");
    var match = value.match(/T(\d{2}):(\d{2})/);
    if (!match) return null;
    var hours = Number(match[1]);
    var minutes = Number(match[2]);
    // Midnight is commonly used by sources for date-only events.
    if (hours === 0 && minutes === 0) return null;
    if (hours > 23 || minutes > 59) return null;
    return hours * 60 + minutes;
}

function calendarTimeLabel(event) {
    var minutes = calendarStartTime(event);
    if (minutes === null) return "Time TBC";
    var hour = Math.floor(minutes / 60);
    var minute = minutes % 60;
    return String((hour % 12) || 12) + ":" +
        String(minute).padStart(2, "0") + (hour < 12 ? " am" : " pm");
}

function renderDayDetails() {
    var panel = document.getElementById("calendar-details");
    panel.replaceChildren();
    panel.classList.toggle("hidden", !selectedDay);
    if (!selectedDay) return;

    var parts = selectedDay.split("-").map(Number);
    var heading = document.createElement("h4");
    heading.textContent = new Intl.DateTimeFormat("en-AU", {
        weekday: "long", day: "numeric", month: "long", year: "numeric"
    }).format(new Date(parts[0], parts[1] - 1, parts[2]));
    panel.appendChild(heading);

    var matching = eventsForDay(selectedDay).slice().sort(function(a, b) {
        var first = calendarStartTime(a);
        var second = calendarStartTime(b);
        if (first === null && second !== null) return 1;
        if (second === null && first !== null) return -1;
        if (first !== null && second !== null && first !== second) return first - second;
        return calendarEventTitle(a).localeCompare(calendarEventTitle(b));
    });

    var count = document.createElement("p");
    count.className = "calendar-details-count";
    count.textContent = matching.length + (matching.length === 1 ? " event" : " events");
    panel.appendChild(count);

    if (!matching.length) {
        var empty = document.createElement("p");
        empty.textContent = "No matching events on this day.";
        panel.appendChild(empty);
        return;
    }

    matching.forEach(function(event) {
        var row = document.createElement("article");
        row.className = "calendar-detail";

        var picture = document.createElement("div");
        picture.className = "calendar-detail-image";
        if (event.image) {
            var img = document.createElement("img");
            img.src = event.image;
            img.alt = "";
            img.loading = "lazy";
            img.addEventListener("error", function() { picture.classList.add("image-unavailable"); img.remove(); });
            picture.appendChild(img);
        } else {
            picture.classList.add("image-unavailable");
        }

        var info = document.createElement("div");
        info.className = "calendar-detail-info";
        var time = document.createElement("div");
        time.className = "calendar-detail-time";
        time.textContent = calendarTimeLabel(event);
        var name = document.createElement("strong");
        name.textContent = calendarEventTitle(event);
        var venue = document.createElement("p");
        venue.textContent = event.venue || event.location || "Venue TBC";
        var categories = document.createElement("div");
        categories.className = "calendar-detail-categories";
        getEventCategories(event).forEach(function(category) {
            var tag = document.createElement("span");
            tag.className = "calendar-detail-category";
            tag.textContent = category;
            tag.style.backgroundColor = CALENDAR_CATEGORY_COLOURS[category] || CALENDAR_CATEGORY_COLOURS.Other;
            categories.appendChild(tag);
        });
        info.append(time, name, venue, categories);
        row.append(picture, info);

        var url = event.link || event.url;
        if (url && /^https?:\/\//i.test(String(url))) {
            var link = document.createElement("a");
            link.className = "calendar-detail-link";
            link.href = url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = "View Event";
            row.appendChild(link);
        }
        panel.appendChild(row);
    });
}


// ======================================
// RENDER MONTHLY CALENDAR
// ======================================

function renderCalendar() {
    if (currentView !== "calendar") {
        return;
    }

    var year = visibleMonth.getFullYear();
    var month = visibleMonth.getMonth();

    document.getElementById(
        "month-title"
    ).textContent = new Intl.DateTimeFormat(
        "en-AU",
        {
            month: "long",
            year: "numeric"
        }
    ).format(visibleMonth);

    var grid = document.getElementById(
        "calendar-grid"
    );

    grid.replaceChildren();

    var offset =
        (new Date(year, month, 1).getDay() + 6) % 7;

    var days = new Date(
        year,
        month + 1,
        0
    ).getDate();

    var total =
        Math.ceil((offset + days) / 7) * 7;

    var today = new Date();

    var todayKey = dateKey(
        today.getFullYear(),
        today.getMonth(),
        today.getDate()
    );

    for (var i = 0; i < total; i++) {
        var day = i - offset + 1;

        var cell = document.createElement("div");
        cell.className = "calendar-cell";

        if (day < 1 || day > days) {
            cell.classList.add("calendar-empty");
            grid.appendChild(cell);
            continue;
        }

        var key = dateKey(year, month, day);

        if (key === todayKey) {
            cell.classList.add("calendar-today");
        }

        if (key === selectedDay) {
            cell.classList.add("calendar-selected");
        }

        var matching = eventsForDay(key);

        var dateButton = document.createElement(
            "button"
        );

        dateButton.type = "button";
        dateButton.className = "calendar-day-number";
        dateButton.textContent = day;

        dateButton.setAttribute(
            "aria-label",
            key + ": " + matching.length + " events"
        );

        dateButton.addEventListener(
            "click",
            (function(k) {
                return function() {
                    showDay(k);
                };
            })(key)
        );

        cell.appendChild(dateButton);

        matching.slice(0, 8).forEach(
            function(event) {
                var pill = document.createElement(
                    "button"
                );

                pill.type = "button";
                pill.className = "calendar-event";
                pill.style.backgroundColor = calendarCategoryColour(event);
                pill.style.borderLeftColor = calendarCategoryColour(event);
                pill.style.color = "#ffffff";
                pill.setAttribute("aria-label", calendarCategory(event) + ": " + calendarEventTitle(event));

                pill.textContent =
                    calendarEventTitle(event);

                pill.title =
                    event.title || "Untitled Event";

                pill.addEventListener(
                    "click",
                    (function(k) {
                        return function() {
                            showDay(k);
                        };
                    })(key)
                );

                cell.appendChild(pill);
            }
        );

        if (matching.length > 8) {
            var more = document.createElement(
                "button"
            );

            more.type = "button";
            more.className = "calendar-more";

            more.textContent =
                "+" + (matching.length - 8) + " more";

            more.addEventListener(
                "click",
                (function(k) {
                    return function() {
                        showDay(k);
                    };
                })(key)
            );

            cell.appendChild(more);
        }

        grid.appendChild(cell);
    }

    renderCalendarLegend();
    renderDayDetails();
}

// ======================================
// CHANGE BETWEEN CARDS AND CALENDAR
// ======================================

function setView(view) {
    currentView = view;

    var calendar = view === "calendar";

    // Reset the duration filter on every view switch.
    // Disabled makes the checked Calendar setting visibly greyed out.
    if (hideLongEventsInput) {
        hideLongEventsInput.checked = calendar;
        hideLongEventsInput.disabled = calendar;
    }

    document.getElementById(
        "calendar-view"
    ).classList.toggle(
        "hidden",
        !calendar
    );

    eventsContainer.classList.toggle(
        "hidden",
        view !== "cards"
    );
    agendaContainer.classList.toggle("hidden", view !== "agenda");
    document.getElementById("view-agenda").classList.toggle("active", view === "agenda");

    document.getElementById(
        "view-cards"
    ).classList.toggle(
        "active",
        view === "cards"
    );

    document.getElementById(
        "view-calendar"
    ).classList.toggle(
        "active",
        calendar
    );

    noResults.classList.toggle(
        "hidden",
        view !== "cards" ||
        filteredEventsForCalendar.length > 0
    );

    // Reapply filters so the calendar-only exclusions never carry into Cards.
    applyFilters();
}

function changeMonth(delta) {
    visibleMonth = new Date(
        visibleMonth.getFullYear(),
        visibleMonth.getMonth() + delta,
        1
    );

    selectedDay = "";

    renderCalendar();
}

// ======================================
// VIEW BUTTONS
// ======================================

document.getElementById(
    "view-cards"
).addEventListener(
    "click",
    function() {
        setView("cards");
    }
);

document.getElementById(
    "view-calendar"
).addEventListener(
    "click",
    function() {
        setView("calendar");
    }
);

// ======================================
// CALENDAR NAVIGATION
// ======================================

document.getElementById(
    "month-prev"
).addEventListener(
    "click",
    function() {
        changeMonth(-1);
    }
);

document.getElementById(
    "month-next"
).addEventListener(
    "click",
    function() {
        changeMonth(1);
    }
);

document.getElementById(
    "month-today"
).addEventListener(
    "click",
    function() {
        visibleMonth = new Date(
            new Date().getFullYear(),
            new Date().getMonth(),
            1
        );

        selectedDay = "";

        renderCalendar();
    }
);

// ======================================
// CATEGORY DROPDOWN
// ======================================

festivalFilter.addEventListener("click", function() {
    var opening = festivalOptions.classList.contains("hidden");
    if (opening) {
        closeCategoryOptions();
        closeVenueOptions();
    }
    festivalOptions.classList.toggle("hidden", !opening);
    festivalFilter.setAttribute("aria-expanded", opening ? "true" : "false");
});
document.addEventListener("click", function(event) {
    if (!festivalMultiselect.contains(event.target)) closeFestivalOptions();
});
document.addEventListener("keydown", function(event) {
    if (event.key === "Escape") closeFestivalOptions();
});

categoryFilter.addEventListener(
    "click",
    function() {
        var isHidden =
            categoryOptions.classList.contains("hidden");

        if (isHidden) {
            closeVenueOptions();
            closeFestivalOptions();
        }

        categoryOptions.classList.toggle(
            "hidden",
            !isHidden
        );

        categoryFilter.setAttribute(
            "aria-expanded",
            isHidden ? "true" : "false"
        );
    }
);

document.addEventListener(
    "click",
    function(event) {
        if (
            categoryMultiselect &&
            !categoryMultiselect.contains(event.target)
        ) {
            closeCategoryOptions();
        }
    }
);

// ======================================
// CLEAR ALL FILTERS
// ======================================

function clearAllFilters() {
    clearQuickDateSelection();
    searchInput.value = "";
    dateFromInput.value = "";
    dateToInput.value = "";

    selectedCategories = [];

    if (categoryOptions) {
        categoryOptions.querySelectorAll(
            'input[type="checkbox"]'
        ).forEach(function(checkbox) {
            checkbox.checked = false;
        });
    }

    updateCategoryLabel();
    closeCategoryOptions();

    selectedFestivals = [];
    festivalOptions.querySelectorAll('input[type="checkbox"]').forEach(function(checkbox) {
        checkbox.checked = false;
    });
    updateFestivalLabel();
    closeFestivalOptions();

    selectedVenues = [];

    venueCheckboxes.querySelectorAll(
        'input[type="checkbox"]'
    ).forEach(function(checkbox) {
        checkbox.checked = false;
    });

    venueSearch.value = "";
    filterVenueChoices();
    updateVenueLabel();
    closeVenueOptions();

    sortSelect.value = "date-asc";

    if (pastEventsOnlyInput) pastEventsOnlyInput.checked = false;

    if (hideLongEventsInput) {
        hideLongEventsInput.checked = currentView === "calendar";
        hideLongEventsInput.disabled = currentView === "calendar";
    }

    applyFilters();
}

// ======================================
// FILTER EVENT LISTENERS
// ======================================

searchInput.addEventListener(
    "input",
    applyFilters
);

dateFromInput.addEventListener("change", function() {
    clearQuickDateSelection();
    applyFilters();
});

dateToInput.addEventListener("change", function() {
    clearQuickDateSelection();
    applyFilters();
});

// ======================================
// VENUE DROPDOWN
// ======================================

venueFilter.addEventListener(
    "click",
    function() {
        var opening =
            venueOptions.classList.contains("hidden");

        if (opening) {
            closeCategoryOptions();
            closeFestivalOptions();
        }

        venueOptions.classList.toggle(
            "hidden",
            !opening
        );

        venueFilter.setAttribute(
            "aria-expanded",
            opening ? "true" : "false"
        );

        if (opening) {
            venueSearch.focus();
        }
    }
);

venueSearch.addEventListener(
    "input",
    filterVenueChoices
);

document.addEventListener(
    "click",
    function(event) {
        if (
            venueMultiselect &&
            !venueMultiselect.contains(event.target)
        ) {
            closeVenueOptions();
        }
    }
);

document.addEventListener(
    "keydown",
    function(event) {
        if (event.key === "Escape") {
            closeVenueOptions();
            closeCategoryOptions();
        }
    }
);

sortSelect.addEventListener(
    "change",
    applyFilters
);

if (hideLongEventsInput) {
    hideLongEventsInput.addEventListener(
        "change",
        applyFilters
    );
}

if (pastEventsOnlyInput) pastEventsOnlyInput.addEventListener("change", applyFilters);

clearFiltersButton.addEventListener(
    "click",
    clearAllFilters
);

// ======================================
// LOAD EVENTS.JSON
// ======================================

// Load the current database and a separate historical archive.
// A missing archive is normal on first installation.
Promise.all([
    fetch("events.json").then(function(response) {
        if (!response.ok) throw new Error("Could not load events.json");
        return response.json();
    }),
    fetch("historical_events.json").then(function(response) {
        if (!response.ok) return [];
        return response.json();
    }).catch(function() { return []; })
]).then(function(results) {
    var current = Array.isArray(results[0]) ? results[0] : [];
    var archive = Array.isArray(results[1]) ? results[1] : [];
    var today = new Date();
    var todayString = dateKey(today.getFullYear(), today.getMonth(), today.getDate());
    function isPast(event) {
        var end = getDatePart(getEventEnd(event));
        return Boolean(end && end < todayString);
    }
    function key(event) {
        return [event.title || "", event.venue || "", getEventStart(event), event.link || event.url || ""].join("|").toLowerCase();
    }
    var seen = new Set();
    historicalEvents = archive.concat(current).filter(function(event) {
        if (!isPast(event)) return false;
        var id = key(event);
        if (seen.has(id)) return false;
        seen.add(id);
        return true;
    });
    events = current.filter(function(event) { return !isPast(event); });
    events.concat(historicalEvents).forEach(function(event) {
        if (event.venue) event.venue = canonicalVenue(event.venue);
    });
    // Build dropdown choices using both current and historical records.
    var upcoming = events;
    events = upcoming.concat(historicalEvents);
    populateFilters();
    events = upcoming;
    console.log("Current events:", events.length, "Historical events:", historicalEvents.length);
    applyFilters();
}).catch(function(error) {
    console.error("Error loading event data:", error);
    events = [];
    historicalEvents = [];
    populateFilters();
    applyFilters();
});
