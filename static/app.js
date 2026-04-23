const state = {
    bookmarks: [],
    stats: null,
    timeOrder: "newest",
    view: "current",
    source: "cache",
    account: null,
    activeBookmark: null,
    pageMode: document.body.dataset.pageMode || "dashboard",
    allBookmarksLayout: "card",
    allBookmarksColumns: 5,
    renderedCount: 0,
};

const elements = {
    activeAccount: document.getElementById("activeAccount"),
    authorCount: document.getElementById("authorCount"),
    bookmarksGrid: document.getElementById("bookmarksGrid"),
    closeModalButton: document.getElementById("closeModalButton"),
    copyAuthorsButton: document.getElementById("copyAuthorsButton"),
    copyVisibleButton: document.getElementById("copyVisibleButton"),
    dataMode: document.getElementById("dataMode"),
    downloadVisibleButton: document.getElementById("downloadVisibleButton"),
    emptyState: document.getElementById("emptyState"),
    favoriteCount: document.getElementById("favoriteCount"),
    fetchedAt: document.getElementById("fetchedAt"),
    libraryCount: document.getElementById("libraryCount"),
    libraryMediaSelect: document.getElementById("libraryMediaSelect"),
    libraryQueryInput: document.getElementById("libraryQueryInput"),
    libraryScopeSelect: document.getElementById("libraryScopeSelect"),
    libraryTagInput: document.getElementById("libraryTagInput"),
    mediaViewerDetailsButton: document.getElementById("mediaViewerDetailsButton"),
    mediaViewerFallback: document.getElementById("mediaViewerFallback"),
    mediaViewerFallbackAuthor: document.getElementById("mediaViewerFallbackAuthor"),
    mediaViewerHandle: document.getElementById("mediaViewerHandle"),
    mediaViewerImage: document.getElementById("mediaViewerImage"),
    mediaViewerModal: document.getElementById("mediaViewerModal"),
    mediaViewerOpenLink: document.getElementById("mediaViewerOpenLink"),
    mediaViewerTitle: document.getElementById("mediaViewerTitle"),
    mediaViewerVideo: document.getElementById("mediaViewerVideo"),
    messageBanner: document.getElementById("messageBanner"),
    itemsPerRowInput: document.getElementById("itemsPerRowInput"),
    openFirstButton: document.getElementById("openFirstButton"),
    ownerUsername: document.getElementById("ownerUsername"),
    pageCount: document.getElementById("pageCount"),
    previewDate: document.getElementById("previewDate"),
    previewEmbed: document.getElementById("previewEmbed"),
    previewFallback: document.getElementById("previewFallback"),
    previewFallbackAuthor: document.getElementById("previewFallbackAuthor"),
    previewHandle: document.getElementById("previewHandle"),
    previewImage: document.getElementById("previewImage"),
    previewVideo: document.getElementById("previewVideo"),
    previewMediaChip: document.getElementById("previewMediaChip"),
    previewModal: document.getElementById("previewModal"),
    previewOpenMediaButton: document.getElementById("previewOpenMediaButton"),
    previewOpenLink: document.getElementById("previewOpenLink"),
    previewRawVideoLink: document.getElementById("previewRawVideoLink"),
    previewFavoriteButton: document.getElementById("previewFavoriteButton"),
    previewOwnerChip: document.getElementById("previewOwnerChip"),
    previewTagStatus: document.getElementById("previewTagStatus"),
    previewTagsInput: document.getElementById("previewTagsInput"),
    previewText: document.getElementById("previewText"),
    previewTitle: document.getElementById("previewTitle"),
    refreshButton: document.getElementById("refreshButton"),
    runLibrarySearchButton: document.getElementById("runLibrarySearchButton"),
    saveTagsButton: document.getElementById("saveTagsButton"),
    searchInput: document.getElementById("searchInput"),
    showCurrentButton: document.getElementById("showCurrentButton"),
    showAllBookmarksButton: document.getElementById("showAllBookmarksButton"),
    sortSelect: document.getElementById("sortSelect"),
    statusText: document.getElementById("statusText"),
    taggedCount: document.getElementById("taggedCount"),
    template: document.getElementById("bookmarkCardTemplate"),
    topAuthor: document.getElementById("topAuthor"),
    totalCount: document.getElementById("totalCount"),
    visibleCount: document.getElementById("visibleCount"),
};

const timeOrderButtons = [...document.querySelectorAll("[data-time-order]")];
const layoutModeButtons = [...document.querySelectorAll("[data-layout-mode]")];

const dateFormatter = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
});

function setStatus(message) {
    elements.statusText.textContent = message;
}

function showMessage(message) {
    elements.messageBanner.textContent = message;
    elements.messageBanner.classList.remove("hidden");
}

function hideMessage() {
    elements.messageBanner.classList.add("hidden");
}

function showPreviewTagStatus(message, isError = false) {
    elements.previewTagStatus.textContent = message;
    elements.previewTagStatus.classList.remove("hidden");
    elements.previewTagStatus.style.color = isError ? "#ffc2c2" : "#3dd9b6";
}

function hidePreviewTagStatus() {
    elements.previewTagStatus.classList.add("hidden");
}

function getFavoriteLabel(bookmark) {
    return bookmark?.is_favorite ? "Unfavorite" : "Favorite";
}

function applyFavoriteButtonState(button, bookmark) {
    if (!button) {
        return;
    }

    button.textContent = getFavoriteLabel(bookmark);
    button.classList.toggle("is-favorite", Boolean(bookmark?.is_favorite));
}

function getTopAuthor(bookmarks) {
    if (!bookmarks.length) {
        return "-";
    }

    const counts = new Map();
    for (const bookmark of bookmarks) {
        counts.set(bookmark.screen_name, (counts.get(bookmark.screen_name) || 0) + 1);
    }

    const [author] = [...counts.entries()].sort((left, right) => right[1] - left[1])[0];
    return `@${author}`;
}

function formatBookmarkDate(bookmark) {
    if (!bookmark.created_at_iso) {
        return "Date unavailable";
    }

    return dateFormatter.format(new Date(bookmark.created_at_iso));
}

function isTwitterImageUrl(url) {
    return typeof url === "string" && url.includes("pbs.twimg.com");
}

function getBestImageUrl(bookmark) {
    const candidates = [bookmark.media_url, bookmark.media_thumbnail].filter(Boolean);

    for (const candidate of candidates) {
        if (isTwitterImageUrl(candidate)) {
            if (candidate.includes("name=")) {
                return candidate.replace(/name=[^&]+/, "name=orig");
            }

            const separator = candidate.includes("?") ? "&" : "?";
            return `${candidate}${separator}name=orig`;
        }
    }

    return bookmark.media_thumbnail || bookmark.media_url || "";
}

function buildEmbed(container, bookmark) {
    container.replaceChildren();

    const blockquote = document.createElement("blockquote");
    blockquote.className = "twitter-tweet";
    blockquote.dataset.theme = "dark";

    const anchor = document.createElement("a");
    anchor.href = bookmark.link;
    anchor.textContent = bookmark.link;
    blockquote.appendChild(anchor);
    container.appendChild(blockquote);

    if (window.twttr?.widgets?.load) {
        window.twttr.widgets.load(container);
    }
}

function toggleEmbed(card, button, bookmark) {
    const embed = card.querySelector(".bookmark-embed");
    const isHidden = embed.classList.contains("hidden");

    if (isHidden) {
        buildEmbed(embed, bookmark);
        embed.classList.remove("hidden");
        button.textContent = "Hide Embed";
        return;
    }

    embed.classList.add("hidden");
    embed.replaceChildren();
    button.textContent = "Show Embed";
}

function syncTimeOrderButtons() {
    timeOrderButtons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.timeOrder === state.timeOrder);
    });
}

function setTimeOrder(order) {
    state.timeOrder = order;
    syncTimeOrderButtons();
    resetRenderWindow();
    renderBookmarks();
}

function normalizeColumns(value) {
    const numeric = Number.parseInt(value, 10);
    if (Number.isNaN(numeric)) {
        return 5;
    }

    return Math.max(1, Math.min(8, numeric));
}

function applyAllBookmarksLayout() {
    if (!["all-bookmarks", "favorites"].includes(state.pageMode)) {
        return;
    }

    document.body.classList.toggle("page-all-layout-card", state.allBookmarksLayout === "card");
    document.body.classList.toggle("page-all-layout-list", state.allBookmarksLayout === "list");
    document.body.style.setProperty("--all-bookmarks-columns", String(state.allBookmarksColumns));

    layoutModeButtons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.layoutMode === state.allBookmarksLayout);
    });

    if (elements.itemsPerRowInput) {
        elements.itemsPerRowInput.value = String(state.allBookmarksColumns);
        elements.itemsPerRowInput.disabled = state.allBookmarksLayout === "list";
    }
}

function setAllBookmarksLayout(layoutMode) {
    state.allBookmarksLayout = layoutMode === "list" ? "list" : "card";
    applyAllBookmarksLayout();
    resetRenderWindow();
    renderBookmarks();
}

function setAllBookmarksColumns(value) {
    state.allBookmarksColumns = normalizeColumns(value);
    applyAllBookmarksLayout();
    resetRenderWindow();
    renderBookmarks();
}

function getInitialRenderCount() {
    if (!["all-bookmarks", "favorites"].includes(state.pageMode)) {
        return Number.MAX_SAFE_INTEGER;
    }

    if (state.allBookmarksLayout === "list") {
        return 12;
    }

    return Math.max(20, state.allBookmarksColumns * 4);
}

function resetRenderWindow() {
    state.renderedCount = getInitialRenderCount();
}

function maybeLoadMoreOnScroll() {
    if (!["all-bookmarks", "favorites"].includes(state.pageMode)) {
        return;
    }

    const totalVisible = getFilteredBookmarks().length;
    if (state.renderedCount >= totalVisible) {
        return;
    }

    if (window.innerHeight + window.scrollY < document.documentElement.scrollHeight - 700) {
        return;
    }

    state.renderedCount += Math.max(10, state.allBookmarksColumns * 2);
    renderBookmarks();
}

function getFilteredBookmarks() {
    const query = elements.searchInput.value.trim().toLowerCase();
    const sortMode = elements.sortSelect.value;

    const compareTime = (left, right) => {
        if (state.timeOrder === "oldest") {
            return left.created_at_unix - right.created_at_unix;
        }

        return right.created_at_unix - left.created_at_unix;
    };

    const bookmarks = state.bookmarks.filter((bookmark) => {
        if (!query) {
            return true;
        }

        return [
            bookmark.screen_name,
            bookmark.author_name,
            bookmark.text,
            bookmark.tweet_id,
            bookmark.link,
            ...(bookmark.tags || []),
        ]
            .join(" ")
            .toLowerCase()
            .includes(query);
    });

    if (sortMode === "author") {
        return [...bookmarks].sort(
            (left, right) => left.screen_name.localeCompare(right.screen_name) || compareTime(left, right)
        );
    }

    if (sortMode === "tweet") {
        return [...bookmarks].sort(
            (left, right) => right.tweet_id.localeCompare(left.tweet_id) || compareTime(left, right)
        );
    }

    return [...bookmarks].sort(compareTime);
}

function renderTagList(container, bookmark) {
    container.replaceChildren();

    if (!bookmark.is_current) {
        const archivedChip = document.createElement("span");
        archivedChip.className = "tag-chip tag-chip-archived";
        archivedChip.textContent = "Archived";
        container.appendChild(archivedChip);
    }

    const tags = bookmark.tags || [];
    if (!tags.length) {
        const emptyChip = document.createElement("span");
        emptyChip.className = "tag-chip tag-chip-muted";
        emptyChip.textContent = "No tags";
        container.appendChild(emptyChip);
        return;
    }

    tags.forEach((tag) => {
        const chip = document.createElement("span");
        chip.className = "tag-chip";
        chip.textContent = `#${tag}`;
        container.appendChild(chip);
    });
}

function closePreviewModal() {
    state.activeBookmark = null;
    elements.previewModal.classList.add("hidden");
    elements.previewModal.setAttribute("aria-hidden", "true");
    elements.previewEmbed.replaceChildren();
    elements.previewImage.removeAttribute("src");
    elements.previewImage.classList.add("hidden");
    elements.previewVideo.pause();
    elements.previewVideo.removeAttribute("src");
    elements.previewVideo.removeAttribute("poster");
    elements.previewVideo.load();
    elements.previewVideo.classList.add("hidden");
    elements.previewOpenMediaButton.classList.add("hidden");
    elements.previewRawVideoLink.classList.add("hidden");
    elements.previewRawVideoLink.removeAttribute("href");
    applyFavoriteButtonState(elements.previewFavoriteButton, null);
    document.body.classList.remove("modal-open");
    hidePreviewTagStatus();
}

function closeMediaViewer() {
    elements.mediaViewerModal.classList.add("hidden");
    elements.mediaViewerModal.setAttribute("aria-hidden", "true");
    elements.mediaViewerImage.removeAttribute("src");
    elements.mediaViewerImage.classList.add("hidden");
    elements.mediaViewerVideo.pause();
    elements.mediaViewerVideo.removeAttribute("src");
    elements.mediaViewerVideo.load();
    elements.mediaViewerVideo.classList.add("hidden");
    elements.mediaViewerFallback.classList.add("hidden");
    document.body.classList.remove("media-viewer-open");
}

function openMediaViewer(bookmark) {
    state.activeBookmark = bookmark;
    elements.mediaViewerTitle.textContent = bookmark.author_name || `@${bookmark.screen_name}`;
    elements.mediaViewerHandle.textContent = `@${bookmark.screen_name}`;
    elements.mediaViewerOpenLink.href = bookmark.link;
    elements.mediaViewerFallbackAuthor.textContent = `@${bookmark.screen_name}`;

    elements.mediaViewerImage.classList.add("hidden");
    elements.mediaViewerVideo.classList.add("hidden");
    elements.mediaViewerFallback.classList.add("hidden");

    if (bookmark.media_video_url) {
        elements.mediaViewerVideo.src = `/api/bookmarks/${bookmark.tweet_id}/video`;
        elements.mediaViewerVideo.poster = bookmark.media_thumbnail || "";
        elements.mediaViewerVideo.classList.remove("hidden");
    } else if (bookmark.media_url || bookmark.media_thumbnail) {
        elements.mediaViewerImage.src = getBestImageUrl(bookmark);
        elements.mediaViewerImage.alt = `${bookmark.author_name || bookmark.screen_name} media viewer`;
        elements.mediaViewerImage.classList.remove("hidden");
    } else {
        elements.mediaViewerFallback.classList.remove("hidden");
    }

    elements.mediaViewerModal.classList.remove("hidden");
    elements.mediaViewerModal.setAttribute("aria-hidden", "false");
    document.body.classList.add("media-viewer-open");
}

function openPreviewModal(bookmark) {
    state.activeBookmark = bookmark;
    elements.previewTitle.textContent = bookmark.author_name || `@${bookmark.screen_name}`;
    elements.previewHandle.textContent = `@${bookmark.screen_name}`;
    elements.previewDate.textContent = formatBookmarkDate(bookmark);
    elements.previewOwnerChip.textContent = `Owner @${bookmark.screen_name}`;
    if (bookmark.media_type) {
        elements.previewMediaChip.textContent = `${bookmark.media_type}${bookmark.media_count > 1 ? ` x${bookmark.media_count}` : ""}`;
        elements.previewMediaChip.classList.remove("hidden");
    } else {
        elements.previewMediaChip.classList.add("hidden");
    }
    elements.previewText.textContent = bookmark.text || "No tweet text preview available.";
    elements.previewOpenLink.href = bookmark.link;
    elements.previewFallbackAuthor.textContent = `@${bookmark.screen_name}`;
    elements.previewTagsInput.value = (bookmark.tags || []).join(", ");
    applyFavoriteButtonState(elements.previewFavoriteButton, bookmark);
    elements.previewOpenMediaButton.classList.add("hidden");
    elements.previewRawVideoLink.classList.add("hidden");
    hidePreviewTagStatus();

    elements.previewImage.removeAttribute("src");
    elements.previewImage.classList.add("hidden");
    elements.previewVideo.pause();
    elements.previewVideo.removeAttribute("src");
    elements.previewVideo.removeAttribute("poster");
    elements.previewVideo.classList.add("hidden");

    if (bookmark.media_video_url) {
        elements.previewVideo.src = `/api/bookmarks/${bookmark.tweet_id}/video`;
        elements.previewVideo.poster = bookmark.media_thumbnail || "";
        elements.previewVideo.load();
        elements.previewVideo.classList.remove("hidden");
        elements.previewFallback.classList.add("hidden");
        elements.previewOpenMediaButton.classList.remove("hidden");
        elements.previewRawVideoLink.href = bookmark.media_video_url;
        elements.previewRawVideoLink.classList.remove("hidden");
    } else if (bookmark.media_thumbnail) {
        elements.previewImage.src = bookmark.media_thumbnail;
        elements.previewImage.alt = `${bookmark.author_name || bookmark.screen_name} tweet thumbnail`;
        elements.previewImage.classList.remove("hidden");
        elements.previewFallback.classList.add("hidden");
    } else {
        elements.previewImage.removeAttribute("src");
        elements.previewImage.classList.add("hidden");
        elements.previewFallback.classList.remove("hidden");
    }

    buildEmbed(elements.previewEmbed, bookmark);
    elements.previewModal.classList.remove("hidden");
    elements.previewModal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
}

function updateBookmarkLocally(updatedBookmark) {
    state.bookmarks = state.bookmarks.map((bookmark) => {
        if (bookmark.tweet_id === updatedBookmark.tweet_id) {
            return updatedBookmark;
        }
        return bookmark;
    });

    if (state.activeBookmark?.tweet_id === updatedBookmark.tweet_id) {
        state.activeBookmark = updatedBookmark;
    }

    if (state.view === "favorites" && !updatedBookmark.is_favorite) {
        state.bookmarks = state.bookmarks.filter((bookmark) => bookmark.tweet_id !== updatedBookmark.tweet_id);
    }
}

async function toggleFavorite(bookmark) {
    const payload = await requestJson(`/api/bookmarks/${bookmark.tweet_id}/favorite`, {
        method: "POST",
        body: JSON.stringify({
            is_favorite: !bookmark.is_favorite,
        }),
    });

    updateBookmarkLocally(payload.bookmark);
    renderBookmarks();
    updateStats();
    if (state.activeBookmark?.tweet_id === payload.bookmark.tweet_id) {
        if (payload.bookmark.is_favorite || state.view !== "favorites") {
            openPreviewModal(payload.bookmark);
        } else {
            closePreviewModal();
        }
    }
    setStatus(`${payload.bookmark.is_favorite ? "Saved" : "Removed"} favorite for @${payload.bookmark.screen_name}`);
}

function renderBookmarks() {
    const visibleBookmarks = getFilteredBookmarks();
    const renderedBookmarks = ["all-bookmarks", "favorites"].includes(state.pageMode)
        ? visibleBookmarks.slice(0, state.renderedCount)
        : visibleBookmarks;
    elements.bookmarksGrid.replaceChildren();

    renderedBookmarks.forEach((bookmark, index) => {
        const fragment = elements.template.content.cloneNode(true);
        const card = fragment.querySelector(".bookmark-card");

        card.classList.add(`is-${bookmark.media_type || "no-media"}`);
        card.tabIndex = 0;
        card.setAttribute("role", "button");
        card.setAttribute("aria-label", `Preview tweet by ${bookmark.screen_name}`);

        fragment.querySelector(".bookmark-index").textContent = `#${index + 1}`;
        fragment.querySelector(".bookmark-name").textContent = bookmark.author_name || `@${bookmark.screen_name}`;
        fragment.querySelector(".bookmark-author").textContent = `@${bookmark.screen_name}`;
        fragment.querySelector(".bookmark-id").textContent = `Tweet ID: ${bookmark.tweet_id}`;
        fragment.querySelector(".bookmark-date").textContent = formatBookmarkDate(bookmark);
        fragment.querySelector(".bookmark-text").textContent = bookmark.text || "No tweet text preview available.";

        const fallbackAuthor = fragment.querySelector(".bookmark-media-author");
        fallbackAuthor.textContent = `@${bookmark.screen_name}`;

        const media = fragment.querySelector(".bookmark-media");
        const fallback = fragment.querySelector(".bookmark-media-fallback");
        if (bookmark.media_thumbnail) {
            media.src = bookmark.media_thumbnail;
            media.alt = `${bookmark.author_name || bookmark.screen_name} tweet thumbnail`;
            media.classList.remove("hidden");
            fallback.classList.add("hidden");
        }

        const badge = fragment.querySelector(".bookmark-badge");
        if (bookmark.media_type) {
            badge.textContent = `${bookmark.media_type}${bookmark.media_count > 1 ? ` x${bookmark.media_count}` : ""}`;
            badge.classList.remove("hidden");
        }

        const videoIndicator = fragment.querySelector(".bookmark-video-indicator");
        if (bookmark.media_type === "video" || bookmark.media_type === "animated_gif") {
            videoIndicator.classList.remove("hidden");
        }

        renderTagList(fragment.querySelector(".bookmark-tags"), bookmark);

        const link = fragment.querySelector(".bookmark-link");
        link.href = bookmark.link;

        const mediaButton = fragment.querySelector(".bookmark-media-button");
        mediaButton.addEventListener("click", (event) => {
            event.stopPropagation();
            openMediaViewer(bookmark);
        });

        const favoriteButton = fragment.querySelector(".bookmark-favorite-button");
        applyFavoriteButtonState(favoriteButton, bookmark);
        favoriteButton.addEventListener("click", async (event) => {
            event.stopPropagation();
            await toggleFavorite(bookmark);
        });

        const embedButton = fragment.querySelector(".bookmark-embed-button");
        embedButton.addEventListener("click", (event) => {
            event.stopPropagation();
            toggleEmbed(card, embedButton, bookmark);
        });

        link.addEventListener("click", (event) => {
            event.stopPropagation();
        });

        card.addEventListener("click", (event) => {
            if (event.target.closest(".bookmark-actions, .bookmark-embed")) {
                return;
            }

            openPreviewModal(bookmark);
        });

        card.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                openPreviewModal(bookmark);
            }
        });

        elements.bookmarksGrid.appendChild(fragment);
    });

    const uniqueVisibleAuthors = new Set(visibleBookmarks.map((bookmark) => bookmark.screen_name)).size;
    elements.totalCount.textContent = state.bookmarks.length;
    elements.visibleCount.textContent = visibleBookmarks.length;
    elements.authorCount.textContent = uniqueVisibleAuthors;
    elements.emptyState.classList.toggle("hidden", visibleBookmarks.length > 0);
    elements.openFirstButton.disabled = visibleBookmarks.length === 0;
    elements.copyVisibleButton.disabled = visibleBookmarks.length === 0;
    elements.copyAuthorsButton.disabled = visibleBookmarks.length === 0;
    elements.downloadVisibleButton.disabled = visibleBookmarks.length === 0;

    if (["all-bookmarks", "favorites"].includes(state.pageMode)) {
        window.requestAnimationFrame(maybeLoadMoreOnScroll);
    }
}

function updateStats() {
    if (!state.stats) {
        return;
    }

    elements.pageCount.textContent = state.stats.pages_scanned || 0;
    elements.fetchedAt.textContent = state.stats.fetched_at
        ? new Date(state.stats.fetched_at).toLocaleString()
        : "Not fetched yet";
    elements.topAuthor.textContent = getTopAuthor(state.bookmarks);
    elements.libraryCount.textContent = state.stats.library_total || 0;
    elements.favoriteCount.textContent = state.stats.favorite_total || 0;
    elements.taggedCount.textContent = state.stats.tagged_total || 0;
    elements.activeAccount.textContent = state.account?.account_key || "-";
    elements.ownerUsername.textContent = state.account?.owner_username ? `@${state.account.owner_username}` : "-";

    if (state.view === "library") {
        elements.dataMode.textContent = "Database search view from local SQLite cache";
    } else if (state.view === "favorites") {
        elements.dataMode.textContent = "Favorite bookmarks saved in local SQLite cache";
    } else if (state.source === "empty") {
        elements.dataMode.textContent = "Vercel deployment is ready, but X credentials are not configured yet";
    } else if (state.source === "live") {
        elements.dataMode.textContent = "Fresh pull from X saved into local cache";
    } else {
        elements.dataMode.textContent = "Current bookmarks served from local SQLite cache";
    }
}

async function requestJson(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    const payload = await response.json();
    if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Request failed.");
    }

    return payload;
}

function applyPayload(payload, statusMessage) {
    state.bookmarks = payload.bookmarks;
    state.stats = payload.stats;
    state.view = payload.view;
    state.source = payload.source;
    state.account = payload.account || null;
    if (payload.message) {
        showMessage(payload.message);
    } else {
        hideMessage();
    }
    resetRenderWindow();
    renderBookmarks();
    updateStats();
    setStatus(statusMessage);
}

function resetFilters() {
    elements.searchInput.value = "";
    elements.libraryQueryInput.value = "";
    elements.libraryTagInput.value = "";
    elements.libraryMediaSelect.value = "";
    elements.libraryScopeSelect.value = "all";
    elements.sortSelect.value = "timeline";
    setTimeOrder("newest");
    if (["all-bookmarks", "favorites"].includes(state.pageMode)) {
        setAllBookmarksLayout("card");
        setAllBookmarksColumns(5);
    }
}

async function loadCurrentBookmarks() {
    hideMessage();
    const isFavoritesPage = state.pageMode === "favorites";
    setStatus(isFavoritesPage ? "Loading favorites..." : "Loading current cache...");

    try {
        const payload = await requestJson(isFavoritesPage ? "/api/favorites" : "/api/bookmarks");
        let sourceLabel = "cached";
        if (payload.source === "live") {
            sourceLabel = "freshly fetched";
        } else if (payload.source === "empty") {
            sourceLabel = "without configured X credentials";
        }
        applyPayload(
            payload,
            isFavoritesPage
                ? `Loaded ${payload.stats.loaded_total} favorite bookmarks`
                : `Loaded ${payload.stats.loaded_total} ${sourceLabel} bookmarks`
        );
    } catch (error) {
        state.bookmarks = [];
        renderBookmarks();
        showMessage(error.message);
        setStatus("Load failed");
    }
}

async function refreshBookmarks() {
    hideMessage();
    setStatus("Starting refresh from X...");
    elements.refreshButton.disabled = true;

    try {
        await requestJson("/api/bookmarks/refresh", { method: "POST" });

        while (true) {
            await new Promise((resolve) => window.setTimeout(resolve, 2000));
            const status = await requestJson("/api/bookmarks/refresh-status");

            if (status.running) {
                setStatus("Refreshing from X... still working");
                continue;
            }

            if (status.last_error) {
                throw new Error(status.last_error);
            }

            await loadCurrentBookmarks();
            setStatus("Refresh from X completed");
            break;
        }
    } catch (error) {
        showMessage(error.message);
        setStatus("Refresh failed");
    } finally {
        elements.refreshButton.disabled = false;
    }
}

async function searchLibrary() {
    hideMessage();
    setStatus("Searching local library...");

    const params = new URLSearchParams({
        q: elements.libraryQueryInput.value.trim(),
        tag: elements.libraryTagInput.value.trim(),
        media_type: elements.libraryMediaSelect.value,
        scope: elements.libraryScopeSelect.value,
    });

    try {
        const payload = await requestJson(`/api/library?${params.toString()}`);
        applyPayload(payload, `Found ${payload.stats.loaded_total} bookmarks in library`);
    } catch (error) {
        showMessage(error.message);
        setStatus("Search failed");
    }
}

async function saveTags() {
    if (!state.activeBookmark) {
        return;
    }

    elements.saveTagsButton.disabled = true;
    hidePreviewTagStatus();

    try {
        const payload = await requestJson(`/api/bookmarks/${state.activeBookmark.tweet_id}/tags`, {
            method: "POST",
            body: JSON.stringify({
                tags: elements.previewTagsInput.value,
            }),
        });

        updateBookmarkLocally(payload.bookmark);
        renderBookmarks();
        updateStats();
        openPreviewModal(payload.bookmark);
        showPreviewTagStatus("Tags saved");
        setStatus(`Updated tags for @${payload.bookmark.screen_name}`);
    } catch (error) {
        showPreviewTagStatus(error.message, true);
    } finally {
        elements.saveTagsButton.disabled = false;
    }
}

async function copyText(text, successMessage) {
    await navigator.clipboard.writeText(text);
    setStatus(successMessage);
}

function downloadFile(name, content) {
    const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

elements.refreshButton.addEventListener("click", refreshBookmarks);
elements.searchInput.addEventListener("input", () => {
    resetRenderWindow();
    renderBookmarks();
});
elements.sortSelect.addEventListener("change", () => {
    resetRenderWindow();
    renderBookmarks();
});
elements.runLibrarySearchButton.addEventListener("click", searchLibrary);
elements.showCurrentButton.addEventListener("click", loadCurrentBookmarks);
elements.previewFavoriteButton.addEventListener("click", async () => {
    if (state.activeBookmark) {
        await toggleFavorite(state.activeBookmark);
    }
});
elements.saveTagsButton.addEventListener("click", saveTags);
elements.previewOpenMediaButton.addEventListener("click", () => {
    if (state.activeBookmark) {
        openMediaViewer(state.activeBookmark);
    }
});
elements.previewVideo.addEventListener("error", () => {
    if (state.activeBookmark?.media_video_url) {
        showPreviewTagStatus("Inline video could not play here. Use Open Video Viewer or Open Raw Video.", true);
        elements.previewOpenMediaButton.classList.remove("hidden");
        elements.previewRawVideoLink.href = state.activeBookmark.media_video_url;
        elements.previewRawVideoLink.classList.remove("hidden");
    }
});
elements.closeModalButton.addEventListener("click", closePreviewModal);
document.getElementById("closeMediaViewerButton").addEventListener("click", closeMediaViewer);
elements.mediaViewerDetailsButton.addEventListener("click", () => {
    closeMediaViewer();
    if (state.activeBookmark) {
        openPreviewModal(state.activeBookmark);
    }
});

elements.previewModal.addEventListener("click", (event) => {
    if (event.target.dataset.closeModal === "true") {
        closePreviewModal();
    }
});

elements.mediaViewerModal.addEventListener("click", (event) => {
    if (event.target.dataset.closeMediaViewer === "true") {
        closeMediaViewer();
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !elements.previewModal.classList.contains("hidden")) {
        closePreviewModal();
    }

    if (event.key === "Escape" && !elements.mediaViewerModal.classList.contains("hidden")) {
        closeMediaViewer();
    }
});

window.addEventListener("scroll", maybeLoadMoreOnScroll, { passive: true });

timeOrderButtons.forEach((button) => {
    button.addEventListener("click", () => setTimeOrder(button.dataset.timeOrder));
});

layoutModeButtons.forEach((button) => {
    button.addEventListener("click", () => setAllBookmarksLayout(button.dataset.layoutMode));
});

if (elements.itemsPerRowInput) {
    elements.itemsPerRowInput.addEventListener("input", (event) => {
        setAllBookmarksColumns(event.target.value);
    });
}

[elements.libraryQueryInput, elements.libraryTagInput].forEach((input) => {
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            searchLibrary();
        }
    });
});

elements.copyVisibleButton.addEventListener("click", async () => {
    const visibleBookmarks = getFilteredBookmarks();
    await copyText(
        visibleBookmarks.map((bookmark) => bookmark.link).join("\n"),
        `Copied ${visibleBookmarks.length} links`
    );
});

elements.copyAuthorsButton.addEventListener("click", async () => {
    const visibleAuthors = [...new Set(getFilteredBookmarks().map((bookmark) => `@${bookmark.screen_name}`))];
    await copyText(visibleAuthors.join("\n"), `Copied ${visibleAuthors.length} authors`);
});

elements.openFirstButton.addEventListener("click", () => {
    const [firstBookmark] = getFilteredBookmarks();
    if (firstBookmark) {
        window.open(firstBookmark.link, "_blank", "noopener,noreferrer");
    }
});

elements.downloadVisibleButton.addEventListener("click", () => {
    const lines = ["index,screen_name,author_name,tweet_id,created_at,media_type,tags,link"];
    getFilteredBookmarks().forEach((bookmark, index) => {
        lines.push(
            [
                index + 1,
                bookmark.screen_name,
                bookmark.author_name,
                bookmark.tweet_id,
                bookmark.created_at_iso,
                bookmark.media_type,
                (bookmark.tags || []).join("|"),
                bookmark.link,
            ].join(",")
        );
    });

    downloadFile("visible-bookmarks.csv", lines.join("\n"));
    setStatus("Downloaded visible CSV");
});

syncTimeOrderButtons();
applyAllBookmarksLayout();
resetRenderWindow();
loadCurrentBookmarks();
