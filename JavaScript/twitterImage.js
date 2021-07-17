// ==UserScript==
// @name         Twitter Original Image Redirect
// @description  Redirect twitter images to show the original.
// @icon         https://abs.twimg.com/favicons/twitter.ico
// @author       samiksome
// @version      1.0
// @match        *://pbs.twimg.com/media/*
// @run-at       document-start
// ==/UserScript==

const url = window.location.href;

if (url.endsWith("=orig"))
    return;

let idx = url.lastIndexOf("=");
let originalUrl = url.substring(0, idx) + "=orig";

window.location.replace(originalUrl);
