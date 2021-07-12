// ==UserScript==
// @name         Desktop Wikipedia Redirect
// @description  Redirect mobile wikipedia pages to desktop version.
// @icon         https://en.wikipedia.org/static/favicon/wikipedia.ico
// @author       samiksome
// @version      1.0
// @match        *://en.m.wikipedia.org/*
// @run-at       document-start
// ==/UserScript==

const desktopWikipedia = "https://en.wikipedia.org"
const url = new URL(window.location.href)

if (url.hostname === "en.wikipedia.org")
    return;

window.location.replace(desktopWikipedia + url.pathname + url.search + url.hash);
