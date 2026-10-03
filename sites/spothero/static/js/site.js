/* SpotHero mirror — shared front-end behaviour:
   destination autocomplete, date/time defaults, accordion toggles. */
(function () {
  'use strict';

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'class') node.className = attrs[k];
      else if (k === 'text') node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }

  // ---------------------------------------------------------------- suggest
  var debounceTimer = null;
  document.querySelectorAll('[data-autocomplete]').forEach(function (input) {
    var box = null;
    var kindToggle = input.closest('form').querySelector('[name=search_kind]');

    function close() { if (box) { box.remove(); box = null; } }

    function render(items) {
      close();
      if (!items.length) return;
      box = el('ul', { class: 'suggest-box', role: 'listbox' });
      items.forEach(function (item) {
        var li = el('li', {});
        var a = el('a', {
          href: item.url, role: 'option', text: '',
          'data-type': item.type
        });
        a.appendChild(el('span', { class: 'suggest-type', text: item.type }));
        a.appendChild(document.createTextNode(item.label));
        li.appendChild(a);
        box.appendChild(li);
      });
      input.parentNode.appendChild(box);
    }

    input.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      var q = input.value.trim();
      if (q.length < 2) { close(); return; }
      debounceTimer = setTimeout(function () {
        fetch('/api/suggest?q=' + encodeURIComponent(q))
          .then(function (r) { return r.json(); })
          .then(function (d) { if (document.activeElement === input && input.value.trim() === q) render(d.results || []); })
          .catch(function () {});
      }, 220);
    });
    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' || ev.key === 'Tab') {
        clearTimeout(debounceTimer);
        close();
      }
    });
    input.addEventListener('blur', function () { clearTimeout(debounceTimer); setTimeout(close, 180); });
  });

  // Close any open suggest box the instant the press starts outside it, so the
  // element underneath (e.g. the Find Parking button) receives the click.
  document.addEventListener('mousedown', function (ev) {
    document.querySelectorAll('.suggest-box').forEach(function (box) {
      if (!box.contains(ev.target)) box.remove();
    });
  });

  // -------------------------------------------------- hourly/monthly toggle
  document.querySelectorAll('[data-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var form = btn.closest('form');
      var kindInput = form.querySelector('[name=kind]');
      if (!kindInput) return;
      kindInput.value = btn.getAttribute('data-toggle');
      form.querySelectorAll('[data-toggle]').forEach(function (b) {
        b.classList.toggle('active', b === btn);
      });
      var monthly = kindInput.value === 'monthly';
      var win = form.querySelector('#window-fields');
      var mon = form.querySelector('#monthly-field');
      if (win) win.style.display = monthly ? 'none' : '';
      if (mon) mon.style.display = monthly ? '' : 'none';
    });
  });

  // ------------------------------------------------------------- accordions
  document.querySelectorAll('.accordion-button').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var panel = btn.nextElementSibling;
      var open = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', String(!open));
      panel.style.display = open ? 'none' : 'block';
    });
  });

  // ------------------------------------------------- facility page live quote
  var quoteBox = document.querySelector('[data-quote-widget]');
  if (quoteBox) {
    var fid = quoteBox.getAttribute('data-facility');
    var starts = quoteBox.querySelector('[name=starts]');
    var ends = quoteBox.querySelector('[name=ends]');
    var kindSel = quoteBox.querySelector('select[name=kind]');

    // Event-context boxes have a fixed window (no editable datetime inputs):
    // the server-rendered event quote is authoritative; skip the live requote.
    if (starts && ends) {
      function refresh() {
        var params = new URLSearchParams({
          starts: starts.value, ends: ends.value,
          kind: kindSel ? kindSel.value : 'hourly'
        });
        fetch('/api/facility/' + fid + '/quote?' + params)
          .then(function (r) { return r.json(); })
          .then(function (q) {
            var set = function (sel, v) {
              var n = quoteBox.querySelector(sel);
              if (n) n.textContent = '$' + Number(v).toFixed(2);
            };
            set('[data-quote=subtotal]', q.subtotal);
            set('[data-quote=fee]', q.service_fee);
            set('[data-quote=facfee]', q.facility_fee);
            set('[data-quote=total]', q.total);
          })
          .catch(function () {});
      }
      starts.addEventListener('change', refresh);
      ends.addEventListener('change', refresh);
      if (kindSel) kindSel.addEventListener('change', refresh);
      refresh();
    }
  }

  // ------------------------------------------------------- search date echo
  document.querySelectorAll('.search-form').forEach(function (form) {
    form.addEventListener('submit', function (ev) {
      var dest = form.querySelector('[name=search_string]');
      if (dest && !dest.value.trim()) {
        ev.preventDefault();
        dest.focus();
      }
    });
  });

  // ------------------------------------------------------------- image swap
  document.querySelectorAll('.facility-hero .thumbs img').forEach(function (thumb) {
    thumb.addEventListener('click', function () {
      var main = document.querySelector('.facility-hero .main-img');
      if (main && thumb.src) {
        main.src = thumb.getAttribute('data-full') || thumb.src;
      }
    });
  });
})();
