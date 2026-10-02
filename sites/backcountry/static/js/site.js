// backcountry mirror — small vanilla behaviors (gallery, stars width)
(function () {
  'use strict';

  // gallery thumbnails swap the main image
  var thumbs = document.querySelectorAll('.gallery-thumb');
  var main = document.getElementById('gallery-main-img');
  thumbs.forEach(function (t) {
    t.addEventListener('click', function () {
      if (main && t.dataset.full) { main.src = t.dataset.full; }
      thumbs.forEach(function (x) { x.classList.remove('active'); });
      t.classList.add('active');
    });
  });

  // stars: browsers without attr() width support get the data-rating fallback
  var stars = document.querySelectorAll('.stars[data-rating]');
  stars.forEach(function (s) {
    var v = parseFloat(s.dataset.rating) || 0;
    var after = window.getComputedStyle(s, '::after');
    if (after.width === 'auto' || after.width === '0px') {
      var fill = document.createElement('span');
      fill.className = 'stars-fill';
      fill.style.display = 'inline-block';
      fill.style.width = Math.max(0, Math.min(100, v * 20)) + '%';
      fill.textContent = '★★★★★';
      s.appendChild(fill);
    }
  });
})();
