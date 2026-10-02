"use strict";

// Navigation and disclosures stay usable with native elements when scripts are off.
document.querySelectorAll("[aria-controls]").forEach((button) => {
  if (button.tagName !== "BUTTON" || button.classList.contains("mobile-menu-toggle")) return;
  const panel = document.getElementById(button.getAttribute("aria-controls"));
  if (!panel) return;
  button.addEventListener("click", () => {
    const expanded = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!expanded));
    panel.hidden = expanded;
  });
});

const menuToggle = document.querySelector(".mobile-menu-toggle");
const mainNavigation = document.getElementById("primary-navigation");
if (menuToggle && mainNavigation) {
  menuToggle.addEventListener("click", () => {
    const expanded = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!expanded));
    mainNavigation.classList.toggle("mobile-open", !expanded);
  });
}

document.querySelectorAll(".nav-dropdown").forEach((dropdown) => {
  dropdown.addEventListener("toggle", () => {
    if (!dropdown.open) return;
    document.querySelectorAll(".nav-dropdown").forEach((other) => {
      if (other !== dropdown) other.open = false;
    });
  });
});

document.addEventListener("click", (event) => {
  document.querySelectorAll(".nav-dropdown[open], .share-control[open]").forEach((dropdown) => {
    if (!dropdown.contains(event.target)) dropdown.open = false;
  });
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  document.querySelectorAll(".nav-dropdown[open], .share-control[open]").forEach((dropdown) => {
    dropdown.open = false;
    dropdown.querySelector("summary").focus();
  });
});

document.querySelectorAll("[data-submit-change]").forEach((select) => {
  select.addEventListener("change", () => {
    if (select.form) select.form.requestSubmit();
  });
});

document.querySelectorAll("[data-copy-link]").forEach((button) => {
  button.addEventListener("click", async () => {
    const status = button.parentElement.querySelector(".share-status");
    try {
      await navigator.clipboard.writeText(window.location.href);
      status.textContent = "Link copied.";
    } catch {
      status.textContent = "Copy the page address from your browser’s address bar.";
    }
  });
});
document.querySelectorAll("[data-print]").forEach((button) => {
  button.addEventListener("click", () => window.print());
});

// Original DOJ body content sometimes includes Drupal accordion button markup.
document.querySelectorAll(".rich-content .usa-accordion__button[aria-controls]").forEach((button) => {
  const content = document.getElementById(button.getAttribute("aria-controls"));
  if (content) content.hidden = button.getAttribute("aria-expanded") !== "true";
});

const dateStart = document.getElementById("start-date");
const dateEnd = document.getElementById("end-date");
if (dateStart && dateEnd) {
  const validateDates = () => {
    dateEnd.setCustomValidity(dateStart.value && dateEnd.value && dateEnd.value < dateStart.value
      ? "End Date must be on or after Start Date." : "");
  };
  dateStart.addEventListener("change", validateDates);
  dateEnd.addEventListener("change", validateDates);
  validateDates();
}

// Keyboard users can scroll wide source tables without moving the whole page.
document.querySelectorAll('.rich-content table').forEach((table) => {
  table.tabIndex = 0;
});
