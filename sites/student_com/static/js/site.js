/* student_com mirror — shared client behaviours.
   Search autocomplete, auth modals, bookmark toggle, enquiry modal, recently
   viewed dropdown, announcement rotation, gallery lightbox, FAQ accordions. */
(function () {
  "use strict";

  function post(url, data) {
    const body = new URLSearchParams(data || {});
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": window.CSRF_TOKEN,
      },
      body: body.toString(),
      credentials: "same-origin",
    }).then(function (r) { return r.json().catch(function () { return {}; }); });
  }

  /* ---------- announcement banner rotation ---------- */
  var slides = document.querySelectorAll("#announce .slide");
  var dots = document.querySelectorAll("#announce .dots button");
  if (slides.length > 1) {
    var idx = 0;
    setInterval(function () {
      idx = (idx + 1) % slides.length;
      slides.forEach(function (s, i) { s.classList.toggle("active", i === idx); });
      dots.forEach(function (d, i) { d.classList.toggle("active", i === idx); });
    }, 5000);
  }

  /* ---------- modals ---------- */
  function openModal(id) {
    var el = document.getElementById(id);
    if (el) el.classList.add("open");
  }
  function closeModal(id) { var el = document.getElementById(id); if (el) el.classList.remove("open"); }
  document.querySelectorAll("[data-close]").forEach(function (btn) {
    btn.addEventListener("click", function () { closeModal(btn.getAttribute("data-close")); });
  });
  document.querySelectorAll(".modal-overlay").forEach(function (ov) {
    ov.addEventListener("click", function (e) { if (e.target === ov) ov.classList.remove("open"); });
  });
  var authOpen = document.getElementById("auth-open");
  if (authOpen) authOpen.addEventListener("click", function () { openModal("auth-modal"); });
  var showRegister = document.getElementById("show-register");
  if (showRegister) showRegister.addEventListener("click", function (e) {
    e.preventDefault(); closeModal("auth-modal"); openModal("register-modal");
  });
  var showLogin = document.getElementById("show-login");
  if (showLogin) showLogin.addEventListener("click", function (e) {
    e.preventDefault(); closeModal("register-modal"); openModal("auth-modal");
  });

  function markInvalid(fieldId, invalid) {
    var f = document.getElementById(fieldId);
    if (f) f.classList.toggle("invalid", invalid);
  }

  document.getElementById("login-form") && document.getElementById("login-form").addEventListener("submit", function (e) {
    e.preventDefault();
    markInvalid("login-email-field", false);
    markInvalid("login-pass-field", false);
    var btn = document.getElementById("login-submit");
    btn.disabled = true; btn.textContent = "Signing in";
    post("/auth/login", {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-pass").value,
    }).then(function (res) {
      btn.disabled = false; btn.textContent = "Log in";
      if (res.ok) { window.location.reload(); }
      else { markInvalid("login-pass-field", true); }
    });
  });

  document.getElementById("register-form") && document.getElementById("register-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var fields = { "reg-first-field": "reg-first", "reg-last-field": "reg-last", "reg-email-field": "reg-email", "reg-pass-field": "reg-pass" };
    Object.keys(fields).forEach(function (fid) {
      var input = document.getElementById(fields[fid]);
      var bad = !input.value || (fid === "reg-email-field" && !/^[^@]+@[^@]+\.[^@]+$/.test(input.value)) ||
        (fid === "reg-pass-field" && input.value.length < 8);
      markInvalid(fid, bad);
    });
    var btn = document.getElementById("register-submit");
    btn.disabled = true;
    post("/auth/register", {
      first_name: document.getElementById("reg-first").value,
      last_name: document.getElementById("reg-last").value,
      email: document.getElementById("reg-email").value,
      password: document.getElementById("reg-pass").value,
    }).then(function (res) {
      btn.disabled = false;
      if (res.ok) { window.location.reload(); }
      else if (res.error) { alert(res.error); }
    });
  });

  var signout = document.getElementById("signout-btn");
  if (signout) signout.addEventListener("click", function () {
    post("/auth/logout", {}).then(function () { window.location.href = "/"; });
  });

  var userMenuBtn = document.getElementById("user-menu-btn");
  var userMenu = document.getElementById("user-menu");
  if (userMenuBtn && userMenu) {
    userMenuBtn.addEventListener("click", function (e) {
      e.stopPropagation(); userMenu.classList.toggle("open");
    });
    document.addEventListener("click", function () { userMenu.classList.remove("open"); });
  }

  /* ---------- recently viewed dropdown ---------- */
  var rvButton = document.getElementById("rv-button");
  var rvDrop = document.getElementById("rv-drop");
  if (rvButton && rvDrop) {
    rvButton.addEventListener("click", function (e) {
      e.stopPropagation(); rvDrop.classList.toggle("open");
    });
    document.addEventListener("click", function (e) {
      if (!rvDrop.contains(e.target)) rvDrop.classList.remove("open");
    });
  }

  /* ---------- search autocomplete ---------- */
  var searchInput = document.getElementById("navbar-search");
  var searchDrop = document.getElementById("search-drop");
  var heroInput = document.getElementById("hero-search");
  var heroDrop = document.getElementById("hero-drop");
  var ICONS = {
    city: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 21s7-5.4 7-11a7 7 0 1 0-14 0c0 5.6 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/></svg>',
    university: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 10l9-5 9 5-9 5-9-5z"/><path d="M7 12v5c0 1.5 2.2 3 5 3s5-1.5 5-3v-5"/></svg>',
    property: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M9 9h6v6H9z"/></svg>',
  };
  function hrefFor(r) {
    if (r.type === "city") return "/us/" + r.state + "/" + r.slug;
    if (r.type === "university") return "/us/" + r.state + "/" + r.city + "/u/" + r.slug;
    return "/us/" + r.state + "/" + r.city + "/p/" + r.slug;
  }
  function wireSearch(input, drop) {
    if (!input || !drop) return;
    var timer = null;
    function render(rows) {
      drop.innerHTML = "";
      if (!rows.length) { drop.classList.remove("open"); return; }
      rows.forEach(function (r) {
        var row = document.createElement("div");
        row.className = "row";
        row.innerHTML = ICONS[r.type] +
          '<div><div class="t">' + r.name + '</div><div class="s">' + r.label + "</div></div>";
        row.addEventListener("click", function () {
          window.location.href = hrefFor(r);
        });
        drop.appendChild(row);
      });
      drop.classList.add("open");
    }
    input.addEventListener("input", function () {
      clearTimeout(timer);
      var q = input.value.trim();
      if (q.length < 2) { drop.classList.remove("open"); return; }
      timer = setTimeout(function () {
        fetch("/search/suggest?q=" + encodeURIComponent(q)).then(function (r) { return r.json(); })
          .then(function (data) { render(data.results || []); });
      }, 180);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        window.location.href = "/search?q=" + encodeURIComponent(input.value.trim());
      }
    });
    document.addEventListener("click", function (e) {
      if (!drop.contains(e.target) && e.target !== input) drop.classList.remove("open");
    });
  }
  wireSearch(searchInput, searchDrop);
  wireSearch(heroInput, heroDrop);

  /* ---------- bookmark toggle ---------- */
  window.toggleBookmark = function (slug, btn, heartId) {
    if (!window.AUTHENTICATED) { openModal("auth-modal"); return; }
    post("/property/" + slug + "/bookmark", {}).then(function (res) {
      if (res.ok !== undefined) {
        if (btn) {
          btn.setAttribute("aria-label", res.bookmarked ? "Remove from saved properties" : "Save property");
          /* keep the visible label in sync with the saved state so the user
             sees the save took effect without a page reload */
          if (btn.id === "save-property-cta") {
            btn.textContent = res.bookmarked ? "♥ Remove from saved properties"
                                              : "♡ Save this property";
          }
        }
        if (heartId) {
          var h = document.getElementById(heartId);
          if (h) h.setAttribute("fill", res.bookmarked ? "#ff5a76" : "none");
        }
        var count = document.getElementById("bookmark-count");
        if (count && res.count !== undefined) count.textContent = res.count;
      }
    });
  };

  /* ---------- FAQ accordions ---------- */
  document.querySelectorAll(".faq-item > button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      btn.parentElement.classList.toggle("open");
    });
  });
})();
