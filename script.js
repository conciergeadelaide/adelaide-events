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


function formatDate(datetime) {

    var date = new Date(datetime);

    return new Intl.DateTimeFormat("en-AU", {
        weekday: "short",
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit"
    }).format(date);
}


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
    badge.textContent = event.category || "Other";


    imageContainer.appendChild(image);
    imageContainer.appendChild(badge);


    var content = document.createElement("div");
    content.className = "event-content";


    var date = document.createElement("div");
    date.className = "event-date";
    date.textContent = formatDate(event.datetime);


    var title = document.createElement("h3");
    title.className = "event-title";
    title.textContent = event.title || "Untitled Event";


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
    link.href = event.url || "#";
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


function populateFilters() {

    categoryFilter.innerHTML =
        "<option value='all'>All categories</option>";

    venueFilter.innerHTML =
        "<option value='all'>All venues</option>";


    var categories = [];
    var venues = [];


    events.forEach(function(event) {

        if (
            event.category &&
            categories.indexOf(event.category) === -1
        ) {
            categories.push(event.category);
        }


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


function applyFilters() {

    var searchText =
        searchInput.value.toLowerCase().trim();

    var dateFrom =
        dateFromInput.value;

    var dateTo =
        dateToInput.value;

    var selectedCategory =
        categoryFilter.value;

    var selectedVenue =
        venueFilter.value;


    var filteredEvents =
        events.filter(function(event) {

            var eventDate =
                new Date(event.datetime);


            var eventDateString =
                eventDate.getFullYear() +
                "-" +
                String(
                    eventDate.getMonth() + 1
                ).padStart(2, "0") +
                "-" +
                String(
                    eventDate.getDate()
                ).padStart(2, "0");


            var searchableText =
                (
                    (event.title || "") +
                    " " +
                    (event.venue || "") +
                    " " +
                    (event.location || "") +
                    " " +
                    (event.category || "")
                ).toLowerCase();


            var matchesSearch =
                searchableText.indexOf(
                    searchText
                ) !== -1;


            var matchesFrom =
                !dateFrom ||
                eventDateString >= dateFrom;


            var matchesTo =
                !dateTo ||
                eventDateString <= dateTo;


            var matchesCategory =
                selectedCategory === "all" ||
                event.category === selectedCategory;


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

        });


    sortEvents(filteredEvents);
}


function sortEvents(eventList) {

    var sortMethod =
        sortSelect.value;


    eventList.sort(function(a, b) {

        if (sortMethod === "date-asc") {

            return (
                new Date(a.datetime) -
                new Date(b.datetime)
            );

        }


        if (sortMethod === "date-desc") {

            return (
                new Date(b.datetime) -
                new Date(a.datetime)
            );

        }


        if (sortMethod === "title") {

            return a.title.localeCompare(
                b.title
            );

        }


        if (sortMethod === "venue") {

            return a.venue.localeCompare(
                b.venue
            );

        }


        return 0;

    });


    displayEvents(eventList);
}


function clearAllFilters() {

    searchInput.value = "";
    dateFromInput.value = "";
    dateToInput.value = "";

    categoryFilter.value = "all";
    venueFilter.value = "all";

    sortSelect.value = "date-asc";

    applyFilters();
}


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
// LOAD EVENTS FROM events.json
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

        console.log(
            "events.json loaded successfully:",
            data.length,
            "events"
        );


        events =
            Array.isArray(data)
                ? data
                : [];


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
