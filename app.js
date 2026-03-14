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

const tabButtons = document.querySelectorAll(".tab-btn");
tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
        const tabId = btn.dataset.tab;

        document.querySelectorAll(".tab-btn").forEach(button => {
            button.classList.remove("active");
        });
        btn.classList.add("active");

        document.querySelectorAll(".tab-panel").forEach(panel => {
            panel.classList.remove("active");
        });
        document.getElementById(tabId).classList.add("active");
    });
});

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener("click", event => {
        event.preventDefault();
        const target = document.querySelector(anchor.getAttribute("href"));
        if (target) {
            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }
    });
});

const navbar = document.querySelector(".navbar");
window.addEventListener("scroll", () => {
    const currentScroll = window.pageYOffset;
    if (currentScroll > 100) {
        navbar.style.background = "rgba(13, 17, 23, 0.98)";
        navbar.style.boxShadow = "0 1px 0 rgba(48, 54, 61, 1)";
    } else {
        navbar.style.background = "rgba(13, 17, 23, 0.95)";
        navbar.style.boxShadow = "none";
    }
});

const observerOptions = {
    threshold: 0.5,
    rootMargin: "0px"
};

const animateValue = (element, start, end, duration) => {
    let startTimestamp = null;
    const step = timestamp => {
        if (!startTimestamp) {
            startTimestamp = timestamp;
        }
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = Math.floor(progress * (end - start) + start);
        element.textContent = value;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
};

const statsObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (!entry.isIntersecting) {
            return;
        }
        const statValues = entry.target.querySelectorAll(".stat-value");
        statValues.forEach(stat => {
            const num = parseInt(stat.textContent, 10);
            if (!Number.isNaN(num)) {
                animateValue(stat, 0, num, 1800);
            }
        });
        statsObserver.unobserve(entry.target);
    });
}, observerOptions);

const heroStats = document.querySelector(".hero-stats");
if (heroStats) {
    statsObserver.observe(heroStats);
}

document.querySelectorAll(".feature-card, .doc-card").forEach(card => {
    card.addEventListener("mouseenter", function () {
        this.style.transform = "translateY(-4px)";
    });

    card.addEventListener("mouseleave", function () {
        this.style.transform = "translateY(0)";
    });
});

const updateStat = (name, value) => {
    const element = document.querySelector(`[data-stat="${name}"]`);
    if (element) {
        element.textContent = String(value);
    }
};

const capabilityCount = matrixRow => Object.entries(matrixRow)
    .filter(([key, value]) => capabilityLabels[key] && value === "supported")
    .length;

const renderSupportCard = (item, matrixRow) => {
    const supportedCapabilities = Object.entries(matrixRow)
        .filter(([key, value]) => capabilityLabels[key] && value === "supported")
        .map(([key]) => capabilityLabels[key] || formatLabel(key));

    return `
        <article class="support-card">
            <div class="support-card-header">
                <div>
                    <h3>${item.name}</h3>
                    <p class="support-module">${item.spec.module}</p>
                </div>
                <span class="support-badge ${item.kind}">
                    ${item.kind === "official_adapter" ? "Official adapter" : "Preview runtime"}
                </span>
            </div>
            <p class="support-note">${item.spec.notes}</p>
            <div class="support-meta">
                <span>${formatLabel(item.spec.support_level)}</span>
                <span>${capabilityCount(matrixRow)} core capabilities</span>
            </div>
            <div class="support-tags">
                ${supportedCapabilities.map(label => `<span class="support-tag">${label}</span>`).join("")}
            </div>
        </article>
    `;
};

const renderEvidenceCard = item => {
    const summary = item.summary || {};
    const statusCounts = summary.status_counts || {};
    const namedCases = Object.entries(summary.named_cases || {}).slice(0, 6);

    return `
        <article class="evidence-card">
            <div class="evidence-card-header">
                <div>
                    <h3>${item.name}</h3>
                    <p>${item.kind === "official_adapter" ? "Official release-gated path" : "Candidate preview path"}</p>
                </div>
                <span class="evidence-badge ${item.ok ? "ok" : "warn"}">
                    ${item.ok ? "Conformant" : "Needs attention"}
                </span>
            </div>
            <div class="evidence-stats">
                <span>${summary.total || 0} local evals</span>
                <span>${statusCounts.completed || 0} completed</span>
                <span>${statusCounts.blocked || 0} blocked</span>
                <span>${statusCounts.review_required || 0} review</span>
            </div>
            <div class="case-pills">
                ${namedCases.map(([alias, result]) => `
                    <span class="case-pill ${result.status || "unknown"}">
                        ${alias}: ${result.status || "missing"}
                    </span>
                `).join("")}
            </div>
        </article>
    `;
};

const loadRuntimeSupport = async () => {
    const summaryElement = document.getElementById("support-summary");
    const supportGrid = document.getElementById("support-grid");
    const evidenceGrid = document.getElementById("evidence-grid");

    if (!summaryElement || !supportGrid || !evidenceGrid) {
        return;
    }

    try {
        const response = await fetch("./runtime-support-manifest.json", { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const manifest = await response.json();
        const inventory = manifest.inventory || [];
        const matrixRows = Object.fromEntries((manifest.matrix || []).map(item => [item.name, item]));
        const evidencePaths = [
            ...(manifest.evidence?.official_adapters || []),
            ...(manifest.evidence?.preview_runtimes || [])
        ];

        const officialCount = inventory.filter(item => item.kind === "official_adapter").length;
        const previewCount = inventory.filter(item => item.kind === "preview_runtime").length;
        const totalEvals = evidencePaths.reduce((sum, item) => sum + (item.summary?.total || 0), 0);
        const passingPaths = evidencePaths.filter(item => item.ok).length;

        updateStat("support-paths", inventory.length);
        updateStat("official-adapters", officialCount);
        updateStat("local-evals", totalEvals);

        summaryElement.innerHTML = `
            <strong>${officialCount}</strong> official adapter,
            <strong>${previewCount}</strong> preview runtime paths,
            <strong>${totalEvals}</strong> packaged local eval cases,
            and <strong>${passingPaths}/${evidencePaths.length}</strong> support paths currently passing their exported release gates.
        `;

        supportGrid.innerHTML = inventory
            .map(item => renderSupportCard(item, matrixRows[item.name] || {}))
            .join("");

        evidenceGrid.innerHTML = evidencePaths
            .map(renderEvidenceCard)
            .join("");
    } catch (error) {
        summaryElement.innerHTML = `
            <strong>Runtime support manifest unavailable.</strong>
            Reload the page or inspect the repository for the latest checked-in support snapshot.
        `;
        supportGrid.innerHTML = "";
        evidenceGrid.innerHTML = "";
        console.error("Failed to load runtime support manifest:", error);
    }
};

loadRuntimeSupport();
