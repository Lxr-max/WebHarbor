// Tumblr mirror — like / follow toggles post to JSON endpoints and update
// the clicked control + the note count in place.
(function () {
  "use strict";

  function postJSON(url) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Accept": "application/json" }
    }).then(function (r) {
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      return r.json();
    });
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".like-btn[data-like-url]");
    if (btn) {
      ev.preventDefault();
      postJSON(btn.dataset.likeUrl).then(function (data) {
        btn.classList.toggle("active", data.liked);
        document.querySelectorAll('[data-live-notes]').forEach(function(e) { e.textContent = data.note_count.toLocaleString() + (e.tagName === 'H2' ? ' notes' : ''); });
        document.querySelectorAll('[data-live-likes]').forEach(function(e) { e.textContent = data.like_count.toLocaleString() + (e.tagName === 'SPAN' ? ' likes' : ''); });
        var card = btn.closest(".post-card");
        if (card) {
          var count = card.querySelector(".note-count");
          var link = count && count.querySelector("a");
          if (link && typeof data.note_count === "number") {
            link.textContent = data.note_count.toLocaleString() + " notes";
          }
        }
      }).catch(function () {
        window.location.href = btn.dataset.likeUrl;
      });
      return;
    }

    var follow = ev.target.closest(".follow-btn[data-follow-url]");
    if (follow) {
      ev.preventDefault();
      postJSON(follow.dataset.followUrl).then(function (data) {
        var label = follow.querySelector(".follow-label");
        follow.classList.toggle("active", data.following);
        if (label) { label.textContent = data.following ? "Following" : "Follow"; }
        // on the Following page an unfollow removes the card outright
        var card = follow.closest(".follow-card");
        if (card && !data.following) {
          card.style.opacity = "0.35";
          card.remove();
        }
      }).catch(function () {
        window.location.href = follow.dataset.followUrl;
      });
    }
  });
})();
