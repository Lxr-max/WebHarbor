/* TourRadar mirror — shared front-end behaviour. */
(function () {
  'use strict';

  // Mega menus: open on click, close on outside click / Escape.
  document.querySelectorAll('.nav-item').forEach(function (item) {
    var btn = item.querySelector('button');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var wasOpen = item.classList.contains('open');
      document.querySelectorAll('.nav-item.open').forEach(function (o) {
        o.classList.remove('open');
      });
      if (!wasOpen) item.classList.add('open');
    });
  });
  document.addEventListener('click', function (e) {
    document.querySelectorAll('.nav-item.open').forEach(function (o) {
      if (!o.contains(e.target)) o.classList.remove('open');
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.nav-item.open').forEach(function (o) {
        o.classList.remove('open');
      });
      document.querySelectorAll('.suggest-box.show').forEach(function (s) {
        s.classList.remove('show');
      });
    }
  });

  // Destination autocomplete for the search widgets.
  var debounce = null;
  document.querySelectorAll('input[data-suggest]').forEach(function (input) {
    var box = input.closest('.field').querySelector('.suggest-box');
    if (!box) return;
    input.addEventListener('input', function () {
      clearTimeout(debounce);
      var q = input.value.trim();
      if (!q) { box.classList.remove('show'); return; }
      debounce = setTimeout(function () {
        fetch('/api/suggest?q=' + encodeURIComponent(q))
          .then(function (r) { return r.json(); })
          .then(function (rows) {
            box.innerHTML = '';
            rows.slice(0, 8).forEach(function (row) {
              var a = document.createElement('a');
              a.href = row.href;
              a.innerHTML = row.label.replace(/</g, '&lt;') +
                ' <span class="kind">' + row.kind + '</span>';
              box.appendChild(a);
            });
            box.classList.toggle('show', rows.length > 0);
          });
      }, 180);
    });
    input.addEventListener('focus', function () {
      if (input.value.trim() && box.children.length) box.classList.add('show');
    });
  });

  // Itinerary accordion.
  document.querySelectorAll('.day-head').forEach(function (head) {
    head.addEventListener('click', function () {
      head.parentElement.classList.toggle('open');
    });
  });
  var expandAll = document.querySelector('[data-expand-all]');
  if (expandAll) {
    expandAll.addEventListener('click', function () {
      var items = document.querySelectorAll('.day-item');
      var anyClosed = false;
      items.forEach(function (i) { if (!i.classList.contains('open')) anyClosed = true; });
      items.forEach(function (i) { i.classList.toggle('open', anyClosed); });
    });
  }

  // Departure "dates & prices" panel.
  var datesToggle = document.querySelector('[data-dates-toggle]');
  var datesPanel = document.querySelector('[data-dates-panel]');
  if (datesToggle && datesPanel) {
    datesToggle.addEventListener('click', function () {
      datesPanel.classList.toggle('hidden');
      datesToggle.scrollIntoView({ block: 'start', behavior: 'smooth' });
    });
  }

  // "Show more dates" in the Dates & Prices panel (upstream paginates the
  // departure list the same way; the first 10 rows render, the rest expand).
  var datesMore = document.querySelector('[data-dates-more]');
  if (datesMore) {
    datesMore.addEventListener('click', function () {
      var collapsed = datesPanel.querySelectorAll('.dep-extra:not(.shown)').length > 0;
      datesPanel.querySelectorAll('.dep-extra').forEach(function (row) {
        if (collapsed) row.classList.add('shown'); else row.classList.remove('shown');
      });
      datesMore.textContent = collapsed ? 'Show fewer dates' : 'Show more dates';
    });
  }

  // Room selection on booking page.
  document.querySelectorAll('.room-option').forEach(function (opt) {
    opt.addEventListener('click', function () {
      document.querySelectorAll('.room-option').forEach(function (o) {
        o.classList.remove('selected');
        var r = o.querySelector('input[type=radio]');
        if (r) r.checked = false;
      });
      opt.classList.add('selected');
      var radio = opt.querySelector('input[type=radio]');
      if (radio) radio.checked = true;
    });
  });
  var defaultRoom = document.querySelector('.room-option input:checked');
  if (defaultRoom) defaultRoom.closest('.room-option').classList.add('selected');

  // Insurance options.
  document.querySelectorAll('.pay-opt').forEach(function (opt) {
    opt.addEventListener('click', function () {
      document.querySelectorAll('.pay-opt').forEach(function (o) {
        o.classList.remove('selected');
      });
      opt.classList.add('selected');
      var radio = opt.querySelector('input[type=radio]');
      if (radio) radio.checked = true;
    });
  });
  var defaultPay = document.querySelector('.pay-opt input:checked');
  if (defaultPay) defaultPay.closest('.pay-opt').classList.add('selected');

  // Traveler count stepper on booking page.
  var stepper = document.querySelector('[data-traveler-stepper]');
  if (stepper) {
    var minus = stepper.querySelector('[data-minus]');
    var plus = stepper.querySelector('[data-plus]');
    var out = stepper.querySelector('[data-count]');
    var form = document.getElementById('booking-form');
    function current() { return parseInt(out.getAttribute('data-count'), 10) || 2; }
    function render(n) {
      out.setAttribute('data-count', n);
      out.textContent = n + (n === 1 ? ' Traveler' : ' Travelers');
      var url = new URL(window.location.href);
      url.searchParams.set('travellers', n);
      window.location.href = url.toString();
    }
    minus.addEventListener('click', function () {
      var n = current();
      if (n > 1) render(n - 1);
    });
    plus.addEventListener('click', function () {
      var n = current();
      if (n < 9) render(n + 1);
    });
  }

  // Search widget: submit to /search with the destination query.
  document.querySelectorAll('form[data-search-form]').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      var input = f.querySelector('input[data-suggest]');
      if (input && input.value.trim()) {
        e.preventDefault();
        var q = input.value.trim();
        var match = q.match(/^\/(d|f|b|v|i)-([a-z0-9-]+)$/);
        if (match) {
          window.location.href = '/srp/' + match[0].slice(1);
        } else {
          window.location.href = '/search?q=' + encodeURIComponent(q);
        }
      }
    });
  });
})();
