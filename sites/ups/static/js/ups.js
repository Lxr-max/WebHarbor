// UPS mirror — client behaviors: nav menus, tracking textarea autosize,
// locator filter sync, quote-table sort (by time / cost).
(function () {
  'use strict';

  // --- header menus ---
  document.querySelectorAll('.ups-navbtn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var group = btn.closest('.ups-navgroup');
      var wasOpen = group.classList.contains('is-open');
      document.querySelectorAll('.ups-navgroup.is-open').forEach(function (g) {
        g.classList.remove('is-open');
        g.querySelector('.ups-navbtn').setAttribute('aria-expanded', 'false');
      });
      if (!wasOpen) {
        group.classList.add('is-open');
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });
  document.addEventListener('click', function () {
    document.querySelectorAll('.ups-navgroup.is-open').forEach(function (g) {
      g.classList.remove('is-open');
      g.querySelector('.ups-navbtn').setAttribute('aria-expanded', 'false');
    });
  });

  // --- tracking textarea: grow with content, submit on Ctrl+Enter ---
  var ta = document.getElementById('trackInput');
  if (ta) {
    var grow = function () {
      ta.style.height = 'auto';
      ta.style.height = Math.min(220, ta.scrollHeight) + 'px';
    };
    ta.addEventListener('input', grow);
    ta.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        ta.form.submit();
      }
    });
    grow();
  }

  // --- quote tables: sort by cost / time ---
  document.querySelectorAll('.ups-quotetable').forEach(function (table) {
    var header = table.querySelector('thead tr');
    if (!header) return;
    var costTh = header.children[header.children.length - 1];
    var timeTh = header.children[1] || null;
    function sortBy(getValue, th) {
      var tbody = table.querySelector('tbody');
      var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
      rows.sort(function (a, b) { return getValue(a) - getValue(b); });
      rows.forEach(function (r) { tbody.appendChild(r); });
      header.querySelectorAll('th').forEach(function (h) { h.classList.remove('is-sorted'); });
      th.classList.add('is-sorted');
    }
    function priceOf(row) {
      var el = row.querySelector('.ups-qprice');
      return el ? parseFloat(el.textContent.replace(/[^0-9.]/g, '')) || 0 : 0;
    }
    function daysOf(row) {
      var el = row.querySelector('td:nth-child(3) strong, td strong');
      return el ? parseInt(el.textContent, 10) || 0 : 0;
    }
    if (costTh) {
      costTh.style.cursor = 'pointer';
      costTh.title = 'Sort by cost';
      costTh.addEventListener('click', function () { sortBy(priceOf, costTh); });
    }
    if (timeTh) {
      timeTh.style.cursor = 'pointer';
      timeTh.title = 'Sort by time';
      timeTh.addEventListener('click', function () { sortBy(daysOf, timeTh); });
    }
  });

  // --- locator: keep the filter chips in sync with the search ---
  var locZip = document.getElementById('loczip');
  document.querySelectorAll('.ups-chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      if (locZip && locZip.value) {
        var url = new URL(chip.href, window.location.origin);
        url.searchParams.set('zip', locZip.value);
        chip.href = url.toString();
      }
    });
  });
})();
