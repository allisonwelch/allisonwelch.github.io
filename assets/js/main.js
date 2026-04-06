// ============================================
// Allison Welch — Site JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Tab active state based on current page
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.tab').forEach(tab => {
        const href = tab.getAttribute('href');
        if (href === currentPage || (currentPage === '' && href === 'index.html')) {
            tab.classList.add('active');
        }
    });

    // Mobile nav toggle
    const navToggle = document.querySelector('.nav-toggle');
    const mobileNav = document.querySelector('.mobile-nav');

    if (navToggle && mobileNav) {
        navToggle.addEventListener('click', () => {
            navToggle.classList.toggle('active');
            mobileNav.classList.toggle('active');
        });

        // Close on link click
        mobileNav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navToggle.classList.remove('active');
                mobileNav.classList.remove('active');
            });
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!navToggle.contains(e.target) && !mobileNav.contains(e.target)) {
                navToggle.classList.remove('active');
                mobileNav.classList.remove('active');
            }
        });

        // Set active state in mobile nav
        mobileNav.querySelectorAll('a').forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPage || (currentPage === '' && href === 'index.html')) {
                link.classList.add('active');
            }
        });
    }

    // Sidebar section scrolling — click to scroll
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    let isClickScrolling = false;

    sidebarItems.forEach(item => {
        item.addEventListener('click', (e) => {
            // Remove selected from all items
            sidebarItems.forEach(i => i.classList.remove('selected'));
            // Add selected to clicked
            item.classList.add('selected');

            // Scroll to the target section
            const targetId = item.getAttribute('href');
            if (targetId && targetId.startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(targetId);
                if (target) {
                    // Temporarily disable scroll-based highlighting during click scroll
                    isClickScrolling = true;
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    // Re-enable after scroll completes
                    setTimeout(() => { isClickScrolling = false; }, 800);
                }
            }
        });
    });

    // Sidebar scroll-based highlighting.
    // Uses proportional scroll-fraction mapping so every sidebar item
    // is guaranteed to highlight at some scroll position.
    // Listens via window capture to catch scroll events from ANY container,
    // and checks all possible scroll ancestors dynamically.
    if (sidebarItems.length > 0) {
        const sections = [];
        const sidebarItemsForSections = [];
        sidebarItems.forEach(item => {
            const href = item.getAttribute('href');
            if (href && href.startsWith('#')) {
                const section = document.querySelector(href);
                if (section) {
                    sections.push(section);
                    sidebarItemsForSections.push(item);
                }
            }
        });

        if (sections.length > 0) {
            function setActive(index) {
                sidebarItems.forEach(i => i.classList.remove('selected'));
                sidebarItemsForSections[index].classList.add('selected');
            }

            // Check all possible scroll containers and return the fraction
            // of the one that actually has scrollable content.
            function getScrollFraction() {
                const candidates = [
                    document.querySelector('.content-body'),
                    document.querySelector('.main-content'),
                    document.documentElement
                ].filter(Boolean);

                for (const el of candidates) {
                    const maxScroll = el.scrollHeight - el.clientHeight;
                    if (maxScroll > 1) {
                        return Math.max(0, Math.min(1, el.scrollTop / maxScroll));
                    }
                }
                return 0;
            }

            // Count items in each section to weight scroll breakpoints.
            // e.g. Talks (1 item) vs Posters (12 items) → breakpoint at 1/13.
            const itemSelector = '.pub-item, .pres-item, .grant-item, .award-item';
            const itemCounts = sections.map(s =>
                s.querySelectorAll(itemSelector).length || 1);
            const totalItems = itemCounts.reduce((a, b) => a + b, 0);

            // Build cumulative breakpoints: [fraction where section ends]
            const breakpoints = [];
            let cumulative = 0;
            for (let i = 0; i < itemCounts.length; i++) {
                cumulative += itemCounts[i];
                breakpoints.push(cumulative / totalItems);
            }

            const highlightCurrentSection = () => {
                if (isClickScrolling) return;

                const fraction = getScrollFraction();

                // Find which section owns this scroll fraction.
                // breakpoints[0] is where section 0 ends, etc.
                let activeIndex = 0;
                for (let i = 0; i < breakpoints.length - 1; i++) {
                    if (fraction >= breakpoints[i]) {
                        activeIndex = i + 1;
                    }
                }
                setActive(activeIndex);
            };

            // Use capture phase on window to intercept scroll events from
            // any element in the DOM — scroll events don't bubble, but they
            // do propagate during the capture phase.
            window.addEventListener('scroll', highlightCurrentSection, { capture: true, passive: true });

            // Do NOT run on DOMContentLoaded — let the HTML default (first
            // item selected) stand. The scroll listener will take over as
            // soon as the user scrolls.
        }
    }

    // Photography lightbox
    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        const lightboxImg = lightbox.querySelector('img');

        document.querySelectorAll('.photo-item img').forEach(img => {
            img.addEventListener('click', () => {
                lightboxImg.src = img.src;
                lightboxImg.alt = img.alt;
                lightbox.classList.add('active');
            });
        });

        lightbox.addEventListener('click', () => {
            lightbox.classList.remove('active');
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                lightbox.classList.remove('active');
            }
        });
    }

    // Smooth fade-in on scroll for items inside main-content
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -30px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.pub-item, .pres-item, .press-item, .blog-post-card, .grant-item, .award-item').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(10px)';
        el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        observer.observe(el);
    });
});
