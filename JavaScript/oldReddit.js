// ==UserScript==
// @name         Old Reddit Redirect
// @description  Redirect reddit to old.reddit.
// @icon         https://raw.githubusercontent.com/tom-james-watson/old-reddit-redirect/master/img/icon48.png
// @author       samiksome
// @version      1.0
// @match        *://reddit.com/*
// @match        *://www.reddit.com/*
// @match        *://np.reddit.com/*
// @match        *://new.reddit.com/*
// @match        *://amp.reddit.com/*
// @run-at       document-start
// ==/UserScript==

// This is simply a user script variant of the extension Old Reddit Redirect by Tom Watson.
// GitHub link of the extension: https://github.com/tom-james-watson/old-reddit-redirect

const oldReddit = "https://old.reddit.com"
const excludedPaths = ["/gallery", "/poll", "/rpan", "/settings", "/topics"];
const url = new URL(window.location.href)

if (url.hostname === "old.reddit.com")
    return;

for (const path of excludedPaths) {
    if (url.pathname.indexOf(path) === 0)
        return;
}

window.location.replace(oldReddit + url.pathname + url.search + url.hash);
