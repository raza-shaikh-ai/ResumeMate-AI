document.addEventListener("DOMContentLoaded", () => {

    // ── 1. Sticky Navbar ─────────────────────────────────────
    const navbar = document.getElementById("navbar");
    window.addEventListener("scroll", () => {
        navbar.classList.toggle("scrolled", window.scrollY > 50);
    });

    // ── 2. Scroll Reveal ─────────────────────────────────────
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("active");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: "0px 0px -50px 0px" });

    document.querySelectorAll(".reveal").forEach(el => revealObserver.observe(el));

    // ── 3. FAQ Accordion ─────────────────────────────────────
    const faqItems = document.querySelectorAll(".faq-item");
    faqItems.forEach(item => {
        item.addEventListener("click", () => {
            faqItems.forEach(other => {
                if (other !== item) other.classList.remove("active");
            });
            item.classList.toggle("active");
        });
    });

    // ── 4. Smooth Scroll ─────────────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            const targetEl = document.querySelector(targetId);
            if (targetEl) {
                e.preventDefault();
                targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ── 5. Hero Title Word Rotation ───────────────────────────
    const words = [
        "ATS-Optimized",
        "Job-Winning",
        "AI-Powered",
        "Interview-Ready",
        "Recruiter-Approved"
    ];

    const el = document.getElementById("wordRotate");
    if (el) {
        let current = 0;

        function rotateWord() {
            // 1. slide current word out (up)
            el.classList.add("leaving");

            el.addEventListener("animationend", function onLeave() {
                el.removeEventListener("animationend", onLeave);
                el.classList.remove("leaving");

                // 2. swap text while invisible
                current = (current + 1) % words.length;
                el.textContent = words[current];

                // 3. slide new word in (from below)
                el.classList.add("entering");
                el.addEventListener("animationend", function onEnter() {
                    el.removeEventListener("animationend", onEnter);
                    el.classList.remove("entering");
                });
            });
        }

        // Start cycling every 2.5 s
        setInterval(rotateWord, 2500);
    }

});