
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

function getEventCategories(event) {
    if (Array.isArray(event.category)) {
        return event.category.filter(function(category) {
            return Boolean(category);
        });
    }

    if (event.category) {
        return [event.category];
    }

    return ["Other"];
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
    return name;
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
        ? "All venues"
        : selectedVenues.length === 1
            ? selectedVenues[0]
            : selectedVenues.length + " venues selected";
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

    var badge = document.createElement("span");
    badge.className = "category-badge";
    badge.textContent = getCategoryText(event);
    badge.style.backgroundColor = calendarCategoryColour(event);
    badge.style.color = "#ffffff";

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

function applyFilters() {
    var searchText =
        searchInput.value.toLowerCase().trim();

    var dateFrom = dateFromInput.value;
    var dateTo = dateToInput.value;


    var hideLongEvents =
        hideLongEventsInput &&
        hideLongEventsInput.checked;

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

            return (
                matchesSearch &&
                matchesFrom &&
                matchesTo &&
                matchesCategory &&
                matchesVenue &&
                matchesFestival &&
                matchesDuration
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

    if (currentView === "calendar") {
        eventCount.textContent =
            eventList.filter(isMajorCalendarEvent).length +
            " major events";

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

// The calendar shows major events only.
// Cards continue to show every event.

var majorCalendarVenues = [
    "adelaide oval",
    "adelaide convention centre",
    "festival theatre",
    "her majesty's theatre",
    "her majestys theatre",
    "adelaide entertainment centre",
    "hindley st music hall",
    "hindley street music hall",
    "coopers stadium",
    "norwood concert hall",
    "immersive light and art",
    "thebarton theatre",
    "adelaide central market",
    "the gov",
    "morphettville racecourse",
    "unibar",
    "uni bar"
];

var majorCalendarSources = [
    "south australia tourism commission",
    "south australian tourism commission",
    "southaustralia.com",
    "adelaide oval",
    "adelaide convention centre",
    "adelaide entertainment centre",
    "hindley st music hall",
    "hindley street music hall",
    "coopers stadium",
    "immersive light and art",
    "candlelight",
    "fever",
    "the gov",
    "morphettville racecourse",
    "adelaide central market",
    "norwood concert hall",
    "thebarton theatre",
    "unibar",
    "uni bar"
];

var majorFestivalNames = [
    "adelaide festival",
    "womadelaide",
    "illuminate adelaide",
    "adelaide film festival",
    "adelaide equestrian festival",
    "adelaide motorsport festival",
    "adelaide vegan festival",
    "gather round",
    "adl fashion week",
    "adelaide fashion week",
    "adelaide grand final",
    "adelaide motogp",
    "feast festival",
    "christmas pageant",
    "nature festival",
    "sala festival",
    "santos tour down under",
    "tour down under",
    "shannons adelaide rally",
    "south australia's history festival",
    "south australias history festival",
    "tasting australia",
    "tarnanthi",
    "liv golf",
    "ozasia festival",
    "adelaide cabaret festival",
    "adelaide guitar festival",
    "dreambig children's festival",
    "dreambig childrens festival",
    "adelaide writers' week",
    "adelaide writers week",
    "adelaide jazz festival",
    "adelaide fringe"
];

function normalizedCalendarText(value) {
    return String(value || "")
        .toLowerCase()
        .replace(/[’‘]/g, "'")
        .replace(/\s+/g, " ")
        .trim();
}

function includesAnyCalendarText(value, phrases) {
    return phrases.some(function(phrase) {
        return value.indexOf(phrase) !== -1;
    });
}

function isFestivalOverview(event) {
    var title = normalizedCalendarText(event.title);

    // Individual Fringe performances should
    // not appear in the major-events calendar.

    if (
        title.indexOf("adelaide fringe") !== -1 ||
        title === "fringe festival"
    ) {
        return (
            /^(?:the )?adelaide fringe(?: festival)?(?: 20\d{2})?$/.test(title) ||
            title === "fringe festival"
        );
    }

    return includesAnyCalendarText(
        title,
        majorFestivalNames
    );
}

function isMajorCalendarEvent(event) {
    var title = normalizedCalendarText(event.title);
    var venue = normalizedCalendarText(event.venue);

    var source = normalizedCalendarText(
        event.source ||
        event.source_name ||
        event.source_url
    );

    var url = normalizedCalendarText(
        event.url || event.link
    );

    var category = normalizedCalendarText(
        getCategoryText(event)
    );

    // Include public demonstrations
    // with a known date.

    var protest =
        /\b(protest|rally|demonstration|march for|peace march|climate strike|solidarity march|vigil)\b/.test(title) &&
        !/\b(comedy|theatre|theater|concert|film|musical|tribute)\b/.test(category);

    if (protest) return true;

    if (isFestivalOverview(event)) {
        return true;
    }

    if (
        title.indexOf("fringe") !== -1 &&
        !isFestivalOverview(event)
    ) {
        return false;
    }

    if (
        venue.indexOf("rhino room") !== -1 ||
        source.indexOf("rhino room") !== -1
    ) {
        return category.indexOf("comedy") !== -1;
    }

    // Adelaide Festival Centre events
    // are included only at these theatres.

    if (
        source.indexOf("adelaide festival centre") !== -1
    ) {
        return (
            venue.indexOf("festival theatre") !== -1 ||
            venue.indexOf("her majesty") !== -1
        );
    }

    if (
        includesAnyCalendarText(
            venue,
            majorCalendarVenues
        )
    ) {
        return true;
    }

    if (
        includesAnyCalendarText(
            source,
            majorCalendarSources
        )
    ) {
        return true;
    }

    if (
        url.indexOf("feverup.com") !== -1 &&
        (
            title.indexOf("candlelight") !== -1 ||
            category.indexOf("music") !== -1
        )
    ) {
        return true;
    }

    return false;
}

function calendarEventTitle(event) {
    return event.title || "Untitled Event";
}

function eventsForDay(key) {
    return filteredEventsForCalendar.filter(
        function(event) {
            if (!isMajorCalendarEvent(event)) {
                return false;
            }

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

function renderDayDetails() {
    var panel = document.getElementById(
        "calendar-details"
    );

    panel.replaceChildren();

    panel.classList.toggle(
        "hidden",
        !selectedDay
    );

    if (!selectedDay) return;

    var parts = selectedDay.split("-").map(Number);

    var heading = document.createElement("h4");

    heading.textContent = new Intl.DateTimeFormat(
        "en-AU",
        {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric"
        }
    ).format(
        new Date(
            parts[0],
            parts[1] - 1,
            parts[2]
        )
    );

    panel.appendChild(heading);

    var matching = eventsForDay(selectedDay);

    if (!matching.length) {
        var empty = document.createElement("p");

        empty.textContent =
            "No matching events on this day.";

        panel.appendChild(empty);
    }

    matching.forEach(function(event) {
        var row = document.createElement("div");
        row.className = "calendar-detail";

        var info = document.createElement("div");

        var name = document.createElement("strong");

        name.textContent =
            event.title || "Untitled Event";

        var details = document.createElement("p");

        details.textContent =
            formatDate(getEventStart(event)) +
            " · " +
            (event.venue || event.location || "Adelaide") +
            " · " +
            getCategoryText(event);

        info.append(name, details);
        row.appendChild(info);

        var url = event.link || event.url;

        if (url) {
            var link = document.createElement("a");

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

        matching.slice(0, 6).forEach(
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

        if (matching.length > 6) {
            var more = document.createElement(
                "button"
            );

            more.type = "button";
            more.className = "calendar-more";

            more.textContent =
                "+" + (matching.length - 6) + " more";

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

    document.getElementById(
        "calendar-view"
    ).classList.toggle(
        "hidden",
        !calendar
    );

    eventsContainer.classList.toggle(
        "hidden",
        calendar
    );

    document.getElementById(
        "view-cards"
    ).classList.toggle(
        "active",
        !calendar
    );

    document.getElementById(
        "view-calendar"
    ).classList.toggle(
        "active",
        calendar
    );

    noResults.classList.toggle(
        "hidden",
        calendar ||
        filteredEventsForCalendar.length > 0
    );

    if (calendar) {
        eventCount.textContent =
            filteredEventsForCalendar.filter(
                isMajorCalendarEvent
            ).length + " major events";

        renderCalendar();
    } else {
        displayEvents(filteredEventsForCalendar);
    }
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
        hideLongEventsInput.checked = false;
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

dateFromInput.addEventListener(
    "change",
    applyFilters
);

dateToInput.addEventListener(
    "change",
    applyFilters
);

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
