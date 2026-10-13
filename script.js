
"use strict";

// ======================================
// ADELAIDE EVENTS — CONCIERGE
// Complete script.js
// ======================================

var events = [];

var eventsContainer = document.getElementById("events");
var searchInput = document.getElementById("search");
var dateFromInput = document.getElementById("date-from");
var dateToInput = document.getElementById("date-to");
var categoryFilter = document.getElementById("category-filter");
var venueFilter = document.getElementById("venue-filter");
var sortSelect = document.getElementById("sort");
var eventCount = document.getElementById("event-count");
var noResults = document.getElementById("no-results");
var clearFiltersButton = document.getElementById("clear-filters");


// ======================================
// DATE HELPERS
// ======================================

// Support both "datetime" and "date".
function getEventStart(event) {
    return event.datetime || event.date || "";
}

// Support both "end_datetime" and "end_date".
function getEventEnd(event) {
    return event.end_datetime ||
           event.end_date ||
           getEventStart(event);
}

// Return YYYY-MM-DD without timezone conversion.
// This avoids shifting an event to the
// previous day in some browsers.
function getDatePart(value) {
    if (!value) {
        return "";
    }

    var match = String(value).match(
        /^(\d{4}-\d{2}-\d{2})/
    );

    return match ? match[1] : "";
}

// Return a sortable timestamp.
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

// Format an event's date for display.
function formatDate(value) {
    if (!value) {
        return "Date to be confirmed";
    }

    var datePart = getDatePart(value);

    if (!datePart) {
        return "Date to be confirmed";
    }

    var parts = datePart.split("-");

    var year = Number(parts[0]);
    var month = Number(parts[1]);
    var day = Number(parts[2]);

    // Construct at midday to avoid
    // timezone-related day shifts.
    var date = new Date(
        year,
        month - 1,
        day,
        12,
        0,
        0
    );

    if (isNaN(date.getTime())) {
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

    // Only display the time when the
    // source provides a non-midnight time.
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
        year,
        month - 1,
        day,
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

    imageContainer.appendChild(image);
    imageContainer.appendChild(badge);

    var content = document.createElement("div");
    content.className = "event-content";

    var date = document.createElement("div");
    date.className = "event-date";
    date.textContent = formatDate(
        getEventStart(event)
    );

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

    venueText.textContent =
        (event.venue || "Adelaide") +
        " · " +
        (event.location || "Adelaide");

    venue.appendChild(venueIcon);
    venue.appendChild(venueText);

    var link = document.createElement("a");
    link.className = "event-link";

    // Support current and older JSON formats.
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

    // Display every matching event.
    // No 50-event or 100-event limit.
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
    categoryFilter.innerHTML =
        "<option value='all'>All categories</option>";

    venueFilter.innerHTML =
        "<option value='all'>All venues</option>";

    // Permanent master category list.
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
            venues.indexOf(event.venue) === -1
        ) {
            venues.push(event.venue);
        }
    });

    categories.sort();
    venues.sort();

    categories.forEach(function(category) {
        var option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        categoryFilter.appendChild(option);
    });

    venues.forEach(function(venue) {
        var option = document.createElement("option");
        option.value = venue;
        option.textContent = venue;
        venueFilter.appendChild(option);
    });
}


// ======================================
// APPLY SEARCH AND FILTERS
// ======================================

function applyFilters() {
    var searchText =
        searchInput.value.toLowerCase().trim();

    var dateFrom = dateFromInput.value;
    var dateTo = dateToInput.value;

    var selectedCategory = categoryFilter.value;
    var selectedVenue = venueFilter.value;

    var filteredEvents = events.filter(
        function(event) {
            var eventDateString = getDatePart(
                getEventStart(event)
            );

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

            // Events with no known date are kept
            // when no date filter is selected.
            var matchesFrom =
                !dateFrom ||
                (
                    eventDateString !== "" &&
                    eventDateString >= dateFrom
                );

            var matchesTo =
                !dateTo ||
                (
                    eventDateString !== "" &&
                    eventDateString <= dateTo
                );

            var matchesCategory =
                selectedCategory === "all" ||
                getEventCategories(event).indexOf(
                    selectedCategory
                ) !== -1;

            var matchesVenue =
                selectedVenue === "all" ||
                event.venue === selectedVenue;

            return (
                matchesSearch &&
                matchesFrom &&
                matchesTo &&
                matchesCategory &&
                matchesVenue
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

    displayEvents(eventList);
}


// ======================================
// CLEAR ALL FILTERS
// ======================================

function clearAllFilters() {
    searchInput.value = "";
    dateFromInput.value = "";
    dateToInput.value = "";

    categoryFilter.value = "all";
    venueFilter.value = "all";
    sortSelect.value = "date-asc";

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

categoryFilter.addEventListener(
    "change",
    applyFilters
);

venueFilter.addEventListener(
    "change",
    applyFilters
);

sortSelect.addEventListener(
    "change",
    applyFilters
);

clearFiltersButton.addEventListener(
    "click",
    clearAllFilters
);


// ======================================
// LOAD EVENTS.JSON
// ======================================

fetch("events.json")
    .then(function(response) {
        if (!response.ok) {
            throw new Error(
                "Could not load events.json"
            );
        }

        return response.json();
    })
    .then(function(data) {
        events = Array.isArray(data) ? data : [];

        console.log(
            "events.json loaded:",
            events.length,
            "events"
        );

        // ==================================
        // REMOVE EVENTS THAT HAVE FINISHED
        // ==================================

        var today = new Date();

        var todayString =
            today.getFullYear() +
            "-" +
            String(today.getMonth() + 1).padStart(2, "0") +
            "-" +
            String(today.getDate()).padStart(2, "0");

        events = events.filter(function(event) {
            var effectiveEnd = getEventEnd(event);

            if (!effectiveEnd) {
                return true;
            }

            var endDateString =
                getDatePart(effectiveEnd);

            if (!endDateString) {
                return true;
            }

            // Keep events until the end of
            // their final calendar day.
            return endDateString >= todayString;
        });

        console.log(
            "Upcoming/current events:",
            events.length
        );

        populateFilters();
        applyFilters();
    })
    .catch(function(error) {
        console.error(
            "Error loading events.json:",
            error
        );

        events = [];
        populateFilters();
        displayEvents([]);
    });
