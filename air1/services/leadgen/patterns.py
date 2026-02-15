"""Built-in software detection patterns.

Each pattern set contains domains, URL patterns, and HTML patterns
used to detect whether a website uses a particular software product.
"""

BUILTIN_PATTERNS: dict[str, dict] = {
    "cloudbeds": {
        "name": "Cloudbeds",
        "website": "https://cloudbeds.com",
        "detection_patterns": {
            "domains": [
                "cloudbeds.com",
                "hotels.cloudbeds.com",
                "mycloudbed.com",
            ],
            "url_patterns": [
                r"cloudbeds\.com/reservation",
                r"hotels\.cloudbeds\.com",
            ],
            "html_patterns": [
                "cloudbeds.com",
                "cloudbeds-widget",
                "cb-booking-engine",
            ],
        },
    },
    "rms-cloud": {
        "name": "RMS Cloud",
        "website": "https://rfrms.com",
        "detection_patterns": {
            "domains": [
                "rfrms.com",
                "rfrms.net",
                "rms.com.au",
                "rmshospitality.com",
            ],
            "url_patterns": [
                r"rfrms\.(com|net)",
                r"rms\.com\.au",
            ],
            "html_patterns": [
                "rfrms.com",
                "rfrms.net",
                "rms-booking",
            ],
        },
    },
    "mews": {
        "name": "Mews",
        "website": "https://mews.com",
        "detection_patterns": {
            "domains": [
                "mews.com",
                "app.mews.com",
                "mews.li",
            ],
            "url_patterns": [
                r"app\.mews\.com",
                r"mews\.li",
            ],
            "html_patterns": [
                "mews.com",
                "mews-distributor",
            ],
        },
    },
    "siteminder": {
        "name": "SiteMinder",
        "website": "https://siteminder.com",
        "detection_patterns": {
            "domains": [
                "siteminder.com",
                "thebookingbutton.com",
                "bookdirect.net",
            ],
            "url_patterns": [
                r"thebookingbutton\.com",
                r"bookdirect\.net",
            ],
            "html_patterns": [
                "thebookingbutton.com",
                "siteminder",
            ],
        },
    },
    "little-hotelier": {
        "name": "Little Hotelier",
        "website": "https://littlehotelier.com",
        "detection_patterns": {
            "domains": [
                "littlehotelier.com",
                "book-directonline.com",
            ],
            "url_patterns": [
                r"littlehotelier\.com",
                r"book-directonline\.com",
            ],
            "html_patterns": [
                "little-hotelier",
                "littlehotelier",
            ],
        },
    },
    "webrezpro": {
        "name": "WebRezPro",
        "website": "https://webrezpro.com",
        "detection_patterns": {
            "domains": [
                "webrezpro.com",
            ],
            "url_patterns": [
                r"webrezpro\.com",
            ],
            "html_patterns": [
                "webrezpro",
            ],
        },
    },
    "ipms247": {
        "name": "eZee/JEPL (iPMS247)",
        "website": "https://ipms247.com",
        "detection_patterns": {
            "domains": [
                "ipms247.com",
            ],
            "url_patterns": [
                r"ipms247\.com",
            ],
            "html_patterns": [
                "ipms247",
            ],
        },
    },
    "synxis": {
        "name": "SynXis (Sabre)",
        "website": "https://synxis.com",
        "detection_patterns": {
            "domains": [
                "synxis.com",
                "windsurfercrs.com",
            ],
            "url_patterns": [
                r"synxis\.com",
                r"windsurfercrs\.com",
            ],
            "html_patterns": [
                "synxis",
                "windsurfercrs",
            ],
        },
    },
    "travelclick": {
        "name": "TravelClick (Amadeus)",
        "website": "https://travelclick.com",
        "detection_patterns": {
            "domains": [
                "travelclick.com",
                "aborestool.com",
                "reservations.travelclick.com",
            ],
            "url_patterns": [
                r"travelclick\.com",
                r"aborestool\.com",
            ],
            "html_patterns": [
                "travelclick",
                "aborestool",
            ],
        },
    },
    "shopify": {
        "name": "Shopify",
        "website": "https://shopify.com",
        "detection_patterns": {
            "domains": [
                "cdn.shopify.com",
                "myshopify.com",
                "shopifycdn.com",
            ],
            "url_patterns": [
                r"cdn\.shopify\.com",
                r"myshopify\.com",
            ],
            "html_patterns": [
                "cdn.shopify.com",
                "Shopify.theme",
                "shopify-section",
                "myshopify.com",
            ],
        },
    },
    "wordpress": {
        "name": "WordPress",
        "website": "https://wordpress.org",
        "detection_patterns": {
            "domains": [],
            "url_patterns": [],
            "html_patterns": [
                "wp-content/",
                "wp-includes/",
                "wp-json",
                'name="generator" content="WordPress',
            ],
        },
    },
    "squarespace": {
        "name": "Squarespace",
        "website": "https://squarespace.com",
        "detection_patterns": {
            "domains": [
                "squarespace.com",
                "sqsp.com",
                "static1.squarespace.com",
            ],
            "url_patterns": [
                r"squarespace\.com",
                r"sqsp\.com",
            ],
            "html_patterns": [
                "squarespace.com",
                "sqsp.com",
                "squarespace-cdn",
            ],
        },
    },
    "wix": {
        "name": "Wix",
        "website": "https://wix.com",
        "detection_patterns": {
            "domains": [
                "wix.com",
                "wixsite.com",
                "parastorage.com",
            ],
            "url_patterns": [
                r"wix\.com",
                r"wixsite\.com",
            ],
            "html_patterns": [
                "wix.com",
                "wixsite.com",
                "parastorage.com",
                "X-Wix-",
            ],
        },
    },
}
