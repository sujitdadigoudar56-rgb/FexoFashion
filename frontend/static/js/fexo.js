document.addEventListener('DOMContentLoaded', function () {
  // ---------- Loader ----------
  var loader = document.getElementById('fx-loader');
  if (loader) {
    window.addEventListener('load', function () {
      setTimeout(function () {
        loader.classList.add('fx-loaded');
        document.body.style.overflow = '';
      }, 900);
    });
  }

  // ---------- Lenis smooth scroll ----------
  var lenis = null;
  if (window.Lenis) {
    lenis = new Lenis({ duration: 1.1, smoothWheel: true });
    function raf(time) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);
  }

  // ---------- Nav show/hide + glass on scroll ----------
  var nav = document.getElementById('fx-nav');
  var lastY = window.scrollY;
  window.addEventListener('scroll', function () {
    var y = window.scrollY;
    if (!nav) return;
    nav.classList.toggle('fx-scrolled', y > 60);
    if (y > lastY && y > 200) {
      nav.classList.add('fx-hide');
    } else {
      nav.classList.remove('fx-hide');
    }
    lastY = y;
  });

  // ---------- GSAP scroll reveals ----------
  if (window.gsap && window.ScrollTrigger) {
    gsap.registerPlugin(ScrollTrigger);
    gsap.utils.toArray('.fx-reveal, .fx-fade-up').forEach(function (el) {
      gsap.to(el, {
        opacity: 1,
        y: 0,
        duration: 1,
        ease: 'power3.out',
        scrollTrigger: { trigger: el, start: 'top 88%' },
      });
    });
  }

  // ---------- Mobile nav toggle ----------
  var toggle = document.querySelector('.fx-mobile-toggle');
  var mobileMenu = document.getElementById('fx-mobile-menu');
  if (toggle && mobileMenu) {
    toggle.addEventListener('click', function () {
      mobileMenu.classList.toggle('fx-open');
    });
  }

  // ---------- Search overlay ----------
  var searchTrigger = document.getElementById('fx-search-trigger');
  var searchOverlay = document.getElementById('fx-search-overlay');
  var searchClose = document.getElementById('fx-search-close');
  var searchInput = document.getElementById('fx-search-input');
  if (searchTrigger && searchOverlay) {
    searchTrigger.addEventListener('click', function () {
      searchOverlay.classList.add('fx-open');
      setTimeout(function () { searchInput && searchInput.focus(); }, 300);
    });
  }
  if (searchClose) {
    searchClose.addEventListener('click', function () {
      searchOverlay.classList.remove('fx-open');
    });
  }
  if (searchInput) {
    var resultsBox = document.getElementById('fx-search-results');
    var timer = null;
    searchInput.addEventListener('input', function () {
      clearTimeout(timer);
      var q = searchInput.value.trim();
      if (q.length < 2) { resultsBox.innerHTML = ''; return; }
      timer = setTimeout(function () {
        fetch('/shop/search-suggestions/?q=' + encodeURIComponent(q))
          .then(function (r) { return r.json(); })
          .then(function (data) {
            resultsBox.innerHTML = data.results.map(function (p) {
              return '<a href="/shop/' + p.slug + '/" class="fx-search-result">' + p.name + '</a>';
            }).join('');
          });
      }, 250);
    });
  }

  // ---------- Auto-dismiss messages ----------
  document.querySelectorAll('.fx-message').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity .4s ease';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 400);
    }, 4200);
  });

  // ---------- Magnetic buttons ----------
  document.querySelectorAll('.fx-magnetic').forEach(function (btn) {
    btn.addEventListener('mousemove', function (e) {
      var rect = btn.getBoundingClientRect();
      var x = e.clientX - rect.left - rect.width / 2;
      var y = e.clientY - rect.top - rect.height / 2;
      btn.style.transform = 'translate(' + x * 0.25 + 'px,' + y * 0.35 + 'px)';
    });
    btn.addEventListener('mouseleave', function () {
      btn.style.transform = 'translate(0,0)';
    });
  });

  // ---------- Cart quantity stepper (client-side, form submits real value) ----------
  document.querySelectorAll('.fx-qty-box').forEach(function (box) {
    var input = box.querySelector('input');
    var minus = box.querySelector('.fx-qty-minus');
    var plus = box.querySelector('.fx-qty-plus');
    if (minus) minus.addEventListener('click', function () {
      input.value = Math.max(0, parseInt(input.value || '1', 10) - 1);
    });
    if (plus) plus.addEventListener('click', function () {
      input.value = parseInt(input.value || '1', 10) + 1;
    });
  });

  // ---------- Product gallery swap ----------
  document.querySelectorAll('.fx-thumb').forEach(function (thumb) {
    thumb.addEventListener('click', function () {
      var main = document.getElementById('fx-main-image');
      if (main) main.src = thumb.dataset.full;
      document.querySelectorAll('.fx-thumb').forEach(function (t) { t.classList.remove('fx-thumb-active'); });
      thumb.classList.add('fx-thumb-active');
    });
  });

  // ---------- Image zoom on product page ----------
  var zoomWrap = document.getElementById('fx-zoom-wrap');
  if (zoomWrap) {
    var zoomImg = zoomWrap.querySelector('img');
    zoomWrap.addEventListener('mousemove', function (e) {
      var rect = zoomWrap.getBoundingClientRect();
      var x = ((e.clientX - rect.left) / rect.width) * 100;
      var y = ((e.clientY - rect.top) / rect.height) * 100;
      zoomImg.style.transformOrigin = x + '% ' + y + '%';
      zoomImg.style.transform = 'scale(1.8)';
    });
    zoomWrap.addEventListener('mouseleave', function () {
      zoomImg.style.transform = 'scale(1)';
    });
  }

  // ---------- 360 viewer (drag through numbered frames, falls back to single image set) ----------
  var viewer360 = document.getElementById('fx-360-viewer');
  if (viewer360) {
    var frames = JSON.parse(viewer360.dataset.frames || '[]');
    var img360 = viewer360.querySelector('img');
    var idx = 0, dragging = false, startX = 0;
    if (frames.length) {
      viewer360.addEventListener('mousedown', function (e) { dragging = true; startX = e.clientX; });
      window.addEventListener('mouseup', function () { dragging = false; });
      window.addEventListener('mousemove', function (e) {
        if (!dragging) return;
        var delta = e.clientX - startX;
        if (Math.abs(delta) > 12) {
          idx = (idx + (delta > 0 ? 1 : -1) + frames.length) % frames.length;
          img360.src = frames[idx];
          startX = e.clientX;
        }
      });
    }
  }
});
