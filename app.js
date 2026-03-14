const capabilityLabels = {
    prompt_inspection: "Prompt inspection",
    tool_call_interception: "Tool call interception",
    shell_enforcement: "Shell enforcement",
    file_read_enforcement: "File read enforcement",
    file_write_enforcement: "File write enforcement",
    http_enforcement: "HTTP enforcement",
    runtime_context_correlation: "Runtime context",
    review_semantics: "Review semantics",
    log_only_semantics: "Log-only semantics"
};

const formatLabel = value => value.replace(/_/g, " ");

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const nav = document.querySelector(".site-header");
const tabButtons = document.querySelectorAll(".tab-btn");
const revealTargets = document.querySelectorAll(".reveal");
const setupTabs = () => {
    tabButtons.forEach(button => {
        button.addEventListener("click", () => {
            const tabId = button.dataset.tab;

            tabButtons.forEach(item => {
                item.classList.remove("active");
                item.setAttribute("aria-selected", "false");
            });

            document.querySelectorAll(".tab-panel").forEach(panel => {
                panel.classList.remove("active");
            });

            button.classList.add("active");
            button.setAttribute("aria-selected", "true");

            const panel = document.getElementById(tabId);
            if (panel) {
                panel.classList.add("active");
            }
        });
    });
};

const setupSmoothScroll = () => {
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener("click", event => {
            const target = document.querySelector(link.getAttribute("href"));
            if (!target) {
                return;
            }

            event.preventDefault();
            target.scrollIntoView({
                behavior: prefersReducedMotion ? "auto" : "smooth",
                block: "start"
            });
        });
    });
};

const setupHeaderState = () => {
    const update = () => {
        if (!nav) {
            return;
        }
        nav.classList.toggle("scrolled", window.scrollY > 24);
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
};

const animateValue = (element, endValue) => {
    if (prefersReducedMotion) {
        element.textContent = String(endValue);
        return;
    }

    const duration = 1200;
    let startTime = null;

    const step = timestamp => {
        if (startTime === null) {
            startTime = timestamp;
        }

        const progress = Math.min((timestamp - startTime) / duration, 1);
        const current = Math.floor(progress * endValue);
        element.textContent = String(current);

        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };

    window.requestAnimationFrame(step);
};

let revealObserver = null;

const observeReveals = elements => {
    const items = [...elements];

    if (!items.length) {
        return;
    }

    if (!("IntersectionObserver" in window) || prefersReducedMotion) {
        items.forEach(target => target.classList.add("is-visible"));
        return;
    }

    if (!revealObserver) {
        revealObserver = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) {
                    return;
                }

                entry.target.classList.add("is-visible");
                revealObserver.unobserve(entry.target);
            });
        }, {
            threshold: 0.16,
            rootMargin: "0px 0px -48px 0px"
        });
    }

    items.forEach(target => revealObserver.observe(target));
};

const setupRevealObserver = () => {
    observeReveals(revealTargets);
};

const updateMetric = (name, value) => {
    const target = document.querySelector(`[data-stat="${name}"]`);
    if (!target) {
        return;
    }
    animateValue(target, value);
};

const capabilityCount = matrixRow => Object.entries(matrixRow)
    .filter(([key, value]) => capabilityLabels[key] && value === "supported")
    .length;

const sortedInventory = inventory => [...inventory].sort((left, right) => {
    if (left.kind === right.kind) {
        return left.name.localeCompare(right.name);
    }
    return left.kind === "official_adapter" ? -1 : 1;
});

const renderSupportCard = (item, matrixRow) => {
    const supportedCapabilities = Object.entries(matrixRow)
        .filter(([key, value]) => capabilityLabels[key] && value === "supported")
        .map(([key]) => capabilityLabels[key]);

    return `
        <article class="support-card reveal">
            <div class="card-topline">
                <span class="kind-badge ${item.kind}">
                    ${item.kind === "official_adapter" ? "Official adapter" : "Preview runtime"}
                </span>
                <span class="level-badge">${formatLabel(item.spec.support_level)}</span>
            </div>
            <h3>${item.name}</h3>
            <p class="module-name">${item.spec.module}</p>
            <p class="card-copy">${item.spec.notes}</p>
            <div class="capability-meta">
                <strong>${capabilityCount(matrixRow)}</strong>
                <span>declared core capabilities</span>
            </div>
            <div class="tag-row">
                ${supportedCapabilities.map(label => `<span class="tag">${label}</span>`).join("")}
            </div>
        </article>
    `;
};

const renderEvidenceCard = item => {
    const summary = item.summary || {};
    const statusCounts = summary.status_counts || {};
    const namedCases = Object.entries(summary.named_cases || {}).slice(0, 4);
    const tone = item.ok ? "ok" : "warn";

    return `
        <article class="evidence-card reveal">
            <div class="card-topline">
                <span class="kind-badge ${item.kind}">
                    ${item.kind === "official_adapter" ? "Release-gated" : "Preview evidence"}
                </span>
                <span class="evidence-badge ${tone}">
                    ${item.ok ? "Passing" : "Needs attention"}
                </span>
            </div>
            <h3>${item.name}</h3>
            <div class="evidence-stats">
                <span>${summary.total || 0} evals</span>
                <span>${statusCounts.completed || 0} completed</span>
                <span>${statusCounts.blocked || 0} blocked</span>
                <span>${statusCounts.review_required || 0} review</span>
            </div>
            <div class="case-list">
                ${namedCases.map(([alias, result]) => `
                    <div class="case-row">
                        <span>${alias}</span>
                        <strong>${result.status || "missing"}</strong>
                    </div>
                `).join("")}
            </div>
        </article>
    `;
};

const formatTimestamp = value => {
    if (!value) {
        return "Manifest timestamp unavailable";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return `Manifest generated at ${value}`;
    }

    return `Manifest generated ${parsed.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short"
    })}`;
};

const loadRuntimeSupport = async () => {
    const releaseSummary = document.getElementById("release-summary");
    const generatedAt = document.getElementById("generated-at");
    const supportSummary = document.getElementById("support-summary");
    const supportGrid = document.getElementById("support-grid");
    const evidenceGrid = document.getElementById("evidence-grid");

    if (!releaseSummary || !generatedAt || !supportSummary || !supportGrid || !evidenceGrid) {
        return;
    }

    try {
        const response = await fetch("./runtime-support-manifest.json", { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const manifest = await response.json();
        const inventory = sortedInventory(manifest.inventory || []);
        const matrixRows = Object.fromEntries((manifest.matrix || []).map(item => [item.name, item]));
        const evidencePaths = [
            ...(manifest.evidence?.official_adapters || []),
            ...(manifest.evidence?.preview_runtimes || [])
        ];

        const officialCount = inventory.filter(item => item.kind === "official_adapter").length;
        const previewCount = inventory.filter(item => item.kind === "preview_runtime").length;
        const totalEvals = evidencePaths.reduce((sum, item) => sum + (item.summary?.total || 0), 0);
        const passingPaths = evidencePaths.filter(item => item.ok).length;

        updateMetric("official-adapters", officialCount);
        updateMetric("preview-paths", previewCount);
        updateMetric("local-evals", totalEvals);

        generatedAt.textContent = formatTimestamp(manifest.generated_at);

        releaseSummary.innerHTML = `
            <strong>${officialCount}</strong> official adapters,
            <strong>${previewCount}</strong> preview runtime path,
            and <strong>${totalEvals}</strong> packaged local evals back the current support claim.
        `;

        supportSummary.innerHTML = `
            <strong>${passingPaths}/${evidencePaths.length}</strong> support paths currently pass their exported release gates or preview evidence checks.
            The manifest behind this page is checked into the repository and updated from the release workflow.
        `;

        supportGrid.innerHTML = inventory
            .map(item => renderSupportCard(item, matrixRows[item.name] || {}))
            .join("");

        evidenceGrid.innerHTML = evidencePaths
            .sort((left, right) => {
                if (left.kind === right.kind) {
                    return left.name.localeCompare(right.name);
                }
                return left.kind === "official_adapter" ? -1 : 1;
            })
            .map(renderEvidenceCard)
            .join("");
        observeReveals([
            ...supportGrid.querySelectorAll(".reveal"),
            ...evidenceGrid.querySelectorAll(".reveal")
        ]);
    } catch (error) {
        releaseSummary.innerHTML = "<strong>Runtime support manifest unavailable.</strong>";
        generatedAt.textContent = "Manifest timestamp unavailable";
        supportSummary.innerHTML = "Reload the page or inspect the repository for the current support snapshot.";
        supportGrid.innerHTML = "";
        evidenceGrid.innerHTML = "";
        console.error("Failed to load runtime support manifest:", error);
    }
};

setupTabs();
setupSmoothScroll();
setupHeaderState();
setupRevealObserver();
loadRuntimeSupport();
