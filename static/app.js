// -- Constants --
const API_BASE = ""; // Empty string makes it use the current domain automatically
const START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

// -- State --
let gameState = {
    moves: [], 
    currentMoveIndex: -1, 
    fens: [START_FEN], 
    isValid: false,
    pgn: "",
    game_id: null
};

let userToken = localStorage.getItem("chess_token") || null;
let userProfile = null;
try {
    const profileData = localStorage.getItem("chess_profile");
    if (profileData && profileData !== "undefined") {
        userProfile = JSON.parse(profileData);
    }
} catch (e) {
    console.error("Failed to parse user profile", e);
}

let board = null;
let game = new Chess(); // Local chess.js instance for move validation/generation

// -- Initialization --
$(document).ready(() => {
    // Initialize Chessboard
    board = Chessboard('board', {
        position: 'start',
        pieceTheme: '/static/pieces/neo/{piece}.png',
        draggable: true,
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
    });

    // Event Listeners
    $('#imageInput').on('change', handleImageUpload);
    $('#pgnInput').on('change', handlePgnUpload);
    $('#exportBtn').on('click', handleExport);
    $('#reviewBtn').on('click', handleGameReview);
    $('#summaryBtn').on('click', handleReviewSummary);
    $('#saveGameBtn').on('click', saveGame);
    $('#btnFlip').on('click', () => board.flip());

    // Trigger validation when metadata changes
    $('#whitePlayer, #blackPlayer, #eventName, #siteName, #gameDate, #roundNum, #gameResult').on('change', validateMoves);

    // Init Auth UI
    updateAuthUI();

    // Board Navigation
    $('#btnStart').on('click', () => goToMove(-1));
    $('#btnPrev').on('click', () => goToMove(gameState.currentMoveIndex - 1));
    $('#btnNext').on('click', () => goToMove(gameState.currentMoveIndex + 1));
    $('#btnEnd').on('click', () => goToMove(gameState.fens.length - 2));

    // Global Key Listener
    $(document).on('keydown', (e) => {
        if (e.key === "ArrowLeft") $('#btnPrev').click();
        if (e.key === "ArrowRight") $('#btnNext').click();
        if (e.key === "f") board.flip(); // Optional hotkey
    });
});


// -- Handlers --

async function handleImageUpload(e) {
    if (!userToken) {
        alert("Please log in with Google first to scan images.");
        // Clear input so same file can be uploaded again if needed
        $('#imageInput').val('');
        return;
    }

    const file = e.target.files[0];
    if (!file) return;

    // Show Loading
    $('#loadingModal').removeClass('hidden');

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${userToken}`
            },
            body: formData
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            if (errData.detail && errData.detail.error === "LIMIT_REACHED") {
                throw new Error("You have reached your daily limit! Please upgrade to Pro to continue scanning games today.");
            }
            throw new Error(errData.detail || "Upload failed");
        }
        const data = await res.json();

        // Initial raw moves
        gameState.moves = data.moves;

        // Render and validate immediately
        renderGrid();
        await validateMoves();

    } catch (err) {
        alert("Error uploading image: " + err.message);
    } finally {
        $('#loadingModal').addClass('hidden');
    }
}

async function validateMoves() {
    // Collect moves from the grid
    const movesToSend = [];
    const rows = $('.move-row');

    rows.each((i, row) => {
        const num = $(row).find('.move-num').text().replace('.', '');
        const white = $(row).find('.move-white input').val().trim() || null;
        const black = $(row).find('.move-black input').val().trim() || null;

        movesToSend.push({
            move_number: parseInt(num),
            white: white === "" ? null : white,
            black: black === "" ? null : black
        });
    });

    const payload = {
        moves: movesToSend,
        white_player: $('#whitePlayer').val(),
        black_player: $('#blackPlayer').val(),
        event: $('#eventName').val(),
        site: $('#siteName').val(),
        date: $('#gameDate').val() ? $('#gameDate').val().replace(/-/g, '.') : "",
        round: $('#roundNum').val(),
        result: $('#gameResult').val()
    };

    try {
        const res = await fetch(`${API_BASE}/api/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        // Update State
        gameState.isValid = data.valid;
        gameState.pgn = data.pgn;
        gameState.moves = data.annotated_moves; // Save validated moves so they can be sent to DB
        gameState.game_id = null; // Clear old game_id as it's a new validation state

        // Re-construct FEN list
        gameState.fens = [START_FEN];
        let lastValidFen = START_FEN;

        // Update UI Validation status
        data.annotated_moves.forEach((row, i) => {
            const rowEl = $(`.move-row[data-idx="${i}"]`);

            // White
            updateCellStatus(rowEl.find('.move-white'), row.white);
            if (row.white && row.white.valid) {
                gameState.fens.push(row.white.fen);
                lastValidFen = row.white.fen;
            } else if (row.white) {
                // Push last valid so navigation doesn't break, or push the error FEN if backend sent it (it sends PREVIOUS fen on error)
                gameState.fens.push(row.white.fen || lastValidFen);
            } else {
                gameState.fens.push(lastValidFen); // Null move?
            }

            // Black
            updateCellStatus(rowEl.find('.move-black'), row.black);
            if (row.black && row.black.valid) {
                gameState.fens.push(row.black.fen);
                lastValidFen = row.black.fen;
            } else if (row.black) {
                gameState.fens.push(row.black.fen || lastValidFen);
            } else {
                gameState.fens.push(lastValidFen);
            }
        });

        // Toggle Export Button
        $('#exportBtn').prop('disabled', !gameState.isValid);
        $('#reviewBtn').prop('disabled', !gameState.isValid);
        $('#saveGameBtn').prop('disabled', !gameState.isValid || !userToken);

        // If we just validated, update board to the "latest" relevant position? 
        // Or keep current? Let's stay current unless out of bounds.
        // Actually best UX: If invalid, jump to the first error? 
        // For now, simple: just refresh view
        updateBoardStatus();

    } catch (err) {
        console.error("Validation error:", err);
    }
}

function updateCellStatus(cell, data) {
    const input = cell.find('input');
    cell.removeClass('bg-green-900/20 bg-red-900/30');
    input.removeClass('text-green-300 text-red-300 line-through');

    if (!data) return; // Empty

    if (data.valid) {
        cell.addClass('bg-green-900/20');
        input.addClass('text-green-300');
    } else {
        cell.addClass('bg-red-900/30');
        input.addClass('text-red-300');
        // cell.attr('title', data.error); // Tooltip
    }
}

function renderGrid() {
    const container = $('#movesGrid');
    container.empty();

    gameState.moves.forEach((row, idx) => {
        const whiteSan = row.white ? (typeof row.white === 'string' ? row.white : row.white.san) : "";
        const blackSan = row.black ? (typeof row.black === 'string' ? row.black : row.black.san) : "";

        const html = `
        <div class="grid grid-cols-[3rem_1fr_1fr] border-b border-gray-700 move-row" data-idx="${idx}">
            <div class="py-2 text-center text-gray-500 font-mono text-sm move-num">${row.move_number}.</div>
            
            <div class="move-cell move-white p-1">
                <input type="text" value="${whiteSan || ''}" 
                    class="move-input w-full h-full bg-transparent text-center focus:outline-none text-gray-200"
                    onchange="validateMoves()"
                    onfocus="highlightMove(${idx}, 'white')">
            </div>
            
            <div class="move-cell move-black p-1 border-l border-gray-700">
                <input type="text" value="${blackSan || ''}" 
                    class="move-input w-full h-full bg-transparent text-center focus:outline-none text-gray-200"
                    onchange="validateMoves()"
                    onfocus="highlightMove(${idx}, 'black')">
            </div>
        </div>
        `;
        container.append(html);
    });
}

// -- Board Interaction --

function goToMove(index) {
    // index is in terms of half-moves (0 = after 1. White, 1 = after 1. Black)
    // -1 = Start Position

    // Bounds check
    if (index < -1) index = -1;
    if (index >= gameState.fens.length - 1) index = gameState.fens.length - 2;

    gameState.currentMoveIndex = index;
    updateBoardStatus();
}

function updateBoardStatus() {
    // The FEN array has Start + valid/invalid states.
    // Index mapping: 
    // -1 -> fens[0] (Start)
    // 0 -> fens[1] (After 1. White)
    // 1 -> fens[2] (After 1. Black)

    const fenIndex = gameState.currentMoveIndex + 1;
    if (fenIndex < 0 || fenIndex >= gameState.fens.length) return;

    const fen = gameState.fens[fenIndex];
    if (fen) {
        board.position(fen);
        game.load(fen);
    }

    // Update active highlight in grid
    $('.move-input').removeClass('ring-2 ring-yellow-500 bg-gray-800 rounded');

    if (gameState.currentMoveIndex >= 0) {
        // Calculate which cell corresponds to this half-move index
        // even index (0, 2...) -> White
        // odd  index (1, 3...) -> Black
        const rowIdx = Math.floor(gameState.currentMoveIndex / 2);
        const isWhite = (gameState.currentMoveIndex % 2) === 0;

        const row = $(`.move-row[data-idx="${rowIdx}"]`);
        const cell = isWhite ? row.find('.move-white input') : row.find('.move-black input');
        cell.addClass('ring-2 ring-yellow-500 bg-gray-800 rounded');

        // Scroll to view
        cell[0].scrollIntoView({ behavior: "smooth", block: "center" });
    }

    // Trigger opening identification
    updateOpening();
}

// -- Opening Identification --
let openingDebounce;
async function updateOpening() {
    // Only send valid FENs up to current move
    const fensToSend = gameState.fens.slice(0, gameState.currentMoveIndex + 2);
    if (fensToSend.length === 0) return;

    clearTimeout(openingDebounce);
    openingDebounce = setTimeout(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/opening`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fens: fensToSend })
            });
            
            if (!res.ok) throw new Error("Opening fetch failed");
            
            const data = await res.json();
            if (data.eco && data.name !== "Unknown Opening") {
                $('#openingEco').text(data.eco);
                $('#openingName').text(data.name);
                $('#openingDisplay').fadeIn();
            } else {
                $('#openingEco').text("???");
                $('#openingName').text("Unknown Opening");
                $('#openingDisplay').fadeOut();
            }
        } catch (e) {
            console.error("Opening error:", e);
        }
    }, 500); // Debounce
}

function highlightMove(rowIdx, color) {
    // Convert row+color to half-move index
    // row 0, white -> 0
    // row 0, black -> 1
    // row 1, white -> 2
    let index = rowIdx * 2;
    if (color === 'black') index += 1;

    goToMove(index);
}

function handleExport() {
    if (!gameState.pgn) return;

    const blob = new Blob([gameState.pgn], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `game_${Date.now()}.pgn`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

async function handlePgnUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    // Show Loading
    $('#loadingModal').removeClass('hidden');

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/api/upload-pgn`, {
            method: 'POST',
            // No auth required for PGN upload right now, but good practice if it changes later
            headers: userToken ? { 'Authorization': `Bearer ${userToken}` } : {},
            body: formData
        });

        if (!res.ok) throw new Error("Upload failed");

        const data = await res.json();

        // Update Metadata
        $('#whitePlayer').val(data.white_player || "?");
        $('#blackPlayer').val(data.black_player || "?");
        $('#eventName').val(data.event || "?");
        $('#siteName').val(data.site || "?");
        $('#gameDate').val(data.date ? data.date.replace(/\./g, '-') : "");
        $('#roundNum').val(data.round || "?");
        $('#gameResult').val(data.result || "*");

        // Update Game State
        gameState.isValid = data.valid;
        gameState.pgn = data.pgn;
        gameState.game_id = null; // Cleared as this is a new game upload

        // Populate Grid (annotated_moves has same structure as validation output)
        gameState.moves = data.annotated_moves;

        renderGrid();

        // Re-construct FEN list logic (Shared with validation)
        gameState.fens = [START_FEN];
        let lastValidFen = START_FEN;

        data.annotated_moves.forEach((row, i) => {
            const rowEl = $(`.move-row[data-idx="${i}"]`);

            // White
            updateCellStatus(rowEl.find('.move-white'), row.white);
            if (row.white && row.white.valid) {
                gameState.fens.push(row.white.fen);
                lastValidFen = row.white.fen;
            } else if (row.white) {
                gameState.fens.push(row.white.fen || lastValidFen);
            } else {
                gameState.fens.push(lastValidFen);
            }

            // Black
            updateCellStatus(rowEl.find('.move-black'), row.black);
            if (row.black && row.black.valid) {
                gameState.fens.push(row.black.fen);
                lastValidFen = row.black.fen;
            } else if (row.black) {
                gameState.fens.push(row.black.fen || lastValidFen);
            } else {
                gameState.fens.push(lastValidFen);
            }
        });

        // Toggle Export Button
        $('#exportBtn').prop('disabled', !gameState.isValid);
        $('#reviewBtn').prop('disabled', !gameState.isValid);
        $('#saveGameBtn').prop('disabled', !gameState.isValid || !userToken);

        updateBoardStatus();

    } catch (err) {
        alert("Error uploading PGN: " + err.message);
    } finally {
        $('#loadingModal').addClass('hidden');
        // Clear input so same file can be uploaded again if needed
        $('#pgnInput').val('');
    }
}

// -- Drag & Drop Logic --

function onDragStart(source, piece, position, orientation) {
    if (game.game_over()) return false;
    if ((game.turn() === 'w' && piece.search(/^b/) !== -1) ||
        (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
        return false;
    }
}

function onDrop(source, target) {
    const move = game.move({
        from: source,
        to: target,
        promotion: 'q'
    });

    if (move === null) return 'snapback';

    updateUIWithMove(move.san);
}

function onSnapEnd() {
    board.position(game.fen());
}

function updateUIWithMove(san) {
    const nextHalfMove = gameState.currentMoveIndex + 1;
    gameState.currentMoveIndex = nextHalfMove; // Update index immediately to prevent snapback

    const rowIdx = Math.floor(nextHalfMove / 2);
    const isWhite = (nextHalfMove % 2) === 0;

    ensureRowExists(rowIdx);

    const row = $(`.move-row[data-idx="${rowIdx}"]`);
    const cell = isWhite ? row.find('.move-white input') : row.find('.move-black input');

    cell.val(san);
    validateMoves();
}

function ensureRowExists(rowIdx) {
    let row = $(`.move-row[data-idx="${rowIdx}"]`);
    if (row.length === 0) {
        const html = `
        <div class="grid grid-cols-[3rem_1fr_1fr] border-b border-gray-700 move-row" data-idx="${rowIdx}">
            <div class="py-2 text-center text-gray-500 font-mono text-sm move-num">${rowIdx + 1}.</div>
            
            <div class="move-cell move-white p-1">
                <input type="text" value="" 
                    class="move-input w-full h-full bg-transparent text-center focus:outline-none text-gray-200"
                    onchange="validateMoves()"
                    onfocus="highlightMove(${rowIdx}, 'white')">
            </div>
            
            <div class="move-cell move-black p-1 border-l border-gray-700">
                <input type="text" value="" 
                    class="move-input w-full h-full bg-transparent text-center focus:outline-none text-gray-200"
                    onchange="validateMoves()"
                    onfocus="highlightMove(${rowIdx}, 'black')">
            </div>
        </div>
        `;
        $('#movesGrid').append(html);
        const container = document.getElementById('movesGrid');
        container.scrollTop = container.scrollHeight;
    }
}

// -- Auth & DB --

async function handleGoogleLogin(response) {
    const idToken = response.credential;
    try {
        const res = await fetch(`${API_BASE}/api/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: idToken })
        });
        if (!res.ok) throw new Error("Login failed");

        const data = await res.json();

        // Save to local storage
        userToken = data.access_token;
        userProfile = data.user;
        localStorage.setItem("chess_token", userToken);
        localStorage.setItem("chess_profile", JSON.stringify(userProfile));

        updateAuthUI();
    } catch (e) {
        alert("Authentication error: " + e.message);
    }
}

function handleLogout() {
    userToken = null;
    userProfile = null;
    localStorage.removeItem("chess_token");
    localStorage.removeItem("chess_profile");
    updateAuthUI();
}

function updateAuthUI() {
    if (userToken && userProfile) {
        $('#googleBtnWrapper').addClass('hidden');
        $('#userInfo').removeClass('hidden');
        $('#userName').text(userProfile.name);
        $('#userAvatar').attr('src', userProfile.picture);
        $('#saveGameBtn').removeClass('hidden');
        $('#loadGameBtn').removeClass('hidden');
        if (gameState.isValid) $('#saveGameBtn').prop('disabled', false);
    } else {
        $('#googleBtnWrapper').removeClass('hidden');
        $('#userInfo').addClass('hidden');
        $('#saveGameBtn').addClass('hidden');
        $('#loadGameBtn').addClass('hidden');
    }
}

async function saveGame() {
    if (!gameState.isValid || !userToken) return;

    const gamePayload = {
        user_email: userProfile.email,
        white_player: $('#whitePlayer').val() || "?",
        black_player: $('#blackPlayer').val() || "?",
        event: $('#eventName').val() || "?",
        site: $('#siteName').val() || "?",
        date: $('#gameDate').val() ? $('#gameDate').val().replace(/-/g, '.') : "",
        round: $('#roundNum').val() || "?",
        result: $('#gameResult').val() || "*",
        pgn: gameState.pgn,
        annotated_moves: gameState.moves
    };

    try {
        const res = await fetch(`${API_BASE}/api/games`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify(gamePayload)
        });

        if (!res.ok) throw new Error("Failed to save game");
        
        const data = await res.json();
        gameState.game_id = data.game_id;
        
        alert("Game saved successfully!");
    } catch (e) {
        alert("Error saving game: " + e.message);
    }
}

let cachedUserGames = []; // Global to hold state for loading

async function fetchUserGames() {
    if (!userToken) return;
    $('#gamesModal').removeClass('hidden');
    $('#gamesListContent').html('<div class="text-center text-gray-400 py-4">Loading...</div>');

    try {
        const res = await fetch(`${API_BASE}/api/games`, {
            headers: { 'Authorization': `Bearer ${userToken}` }
        });
        if (!res.ok) throw new Error("Failed to fetch games");
        const data = await res.json();

        cachedUserGames = data.items || []; // store globally

        let html = '<div class="space-y-2">';
        if (cachedUserGames.length === 0) {
            html += '<div class="text-center text-gray-500 italic py-4">No saved games found.</div>';
        } else {
            cachedUserGames.forEach((g, idx) => {
                const dateObj = new Date(g.created_at || g.date);
                const datePart = isNaN(dateObj) ? (g.date || 'Unknown Date') : dateObj.toLocaleDateString();
                html += `
                    <div class="flex justify-between items-center p-3 bg-gray-900 border border-gray-700 rounded hover:border-gray-500 transition">
                        <div>
                            <div class="font-bold text-gray-200">${g.white_player} vs ${g.black_player}</div>
                            <div class="text-xs text-gray-500">${g.event} • ${datePart}</div>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="loadGameFromObj(${idx})" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs font-semibold">Load</button>
                            <button onclick="deleteGame('${g._id}', ${idx})" class="px-3 py-1 bg-red-600 hover:bg-red-500 rounded text-xs font-semibold flex items-center justify-center" title="Delete Game">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    </div>
                `;
            });
        }
        html += '</div>';
        $('#gamesListContent').html(html);

    } catch (e) {
        $('#gamesListContent').html(`<div class="text-red-400 text-center py-4">Error: ${e.message}</div>`);
    }
}

function loadGameFromObj(gameIndex) {
    const data = cachedUserGames[gameIndex];
    if (!data) return;

    $('#gamesModal').addClass('hidden');

    // Update Metadata UI
    $('#whitePlayer').val(data.white_player || "?");
    $('#blackPlayer').val(data.black_player || "?");
    $('#eventName').val(data.event || "?");
    $('#siteName').val(data.site || "?");
    $('#gameDate').val(data.date ? data.date.replace(/\./g, '-') : "");
    $('#roundNum').val(data.round || "?");
    $('#gameResult').val(data.result || "*");

    // Update Game State
    gameState.isValid = true;
    gameState.pgn = data.pgn || "";
    gameState.moves = data.annotated_moves || [];
    gameState.game_id = data._id;

    renderGrid();

    // Reset the engine and board to start
    game = new Chess();
    gameState.fens = [START_FEN];
    let lastValidFen = START_FEN;

    // Simulate all moves to rebuild the internal `game` state and FEN history
    gameState.moves.forEach((row, i) => {
        const rowEl = $(`.move-row[data-idx="${i}"]`);

        // White
        updateCellStatus(rowEl.find('.move-white'), row.white);
        if (row.white && row.white.valid) {
            try { game.move(row.white.san); } catch (e) { }
            gameState.fens.push(game.fen());
            lastValidFen = game.fen();
        } else if (row.white) {
            gameState.fens.push(row.white.fen || lastValidFen);
        } else {
            gameState.fens.push(lastValidFen);
        }

        // Black
        updateCellStatus(rowEl.find('.move-black'), row.black);
        if (row.black && row.black.valid) {
            try { game.move(row.black.san); } catch (e) { }
            gameState.fens.push(game.fen());
            lastValidFen = game.fen();
        } else if (row.black) {
            gameState.fens.push(row.black.fen || lastValidFen);
        } else {
            gameState.fens.push(lastValidFen);
        }
    });
    $('#exportBtn').prop('disabled', false);
    $('#reviewBtn').prop('disabled', false);
    $('#summaryBtn').removeClass('hidden'); // Allow skipping Stockfish
    goToMove(gameState.fens.length - 2); // go to end of loaded game
}

async function deleteGame(gameId, idx) {
    if (!confirm("Are you sure you want to delete this game? This action cannot be undone.")) return;

    try {
        const res = await fetch(`${API_BASE}/api/games/${gameId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${userToken}` }
        });

        if (!res.ok) throw new Error("Failed to delete game");

        // Remove locally and re-render modal
        cachedUserGames.splice(idx, 1);

        // Sneaky update UI by just retriggering the fetch UI loop based on cached array
        let html = '<div class="space-y-2">';
        if (cachedUserGames.length === 0) {
            html += '<div class="text-center text-gray-500 italic py-4">No saved games found.</div>';
        } else {
            cachedUserGames.forEach((g, newIdx) => {
                const datePart = new Date(g.created_at).toLocaleDateString();
                html += `
                    <div class="flex justify-between items-center p-3 bg-gray-900 border border-gray-700 rounded hover:border-gray-500 transition">
                        <div>
                            <div class="font-bold text-gray-200">${g.white_player} vs ${g.black_player}</div>
                            <div class="text-xs text-gray-500">${g.event} • ${datePart}</div>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="loadGameFromObj(${newIdx})" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs font-semibold">Load</button>
                            <button onclick="deleteGame('${g._id}', ${newIdx})" class="px-3 py-1 bg-red-600 hover:bg-red-500 rounded text-xs font-semibold flex items-center justify-center" title="Delete Game">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    </div>
                `;
            });
        }
        html += '</div>';
        $('#gamesListContent').html(html);

    } catch (e) {
        alert("Error deleting game: " + e.message);
    }
}

// -- Game Review --
async function handleGameReview() {
    if (!gameState.game_id) {
        alert("Please save the game to your profile before generating a review.");
        return;
    }

    $('#reviewModal').removeClass('hidden');
    $('#reviewLoading').removeClass('hidden');
    $('#reviewContent').html('');

    try {
        const res = await fetch(`${API_BASE}/api/review`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify({ game_id: gameState.game_id })
        });

        if (!res.ok) throw new Error("Failed to generate review");

        const data = await res.json();
        
        $('#summaryBtn').removeClass('hidden');
        window.lastLlmPayload = data.llm_payload;

        // 1. Generate SVG Graph
        let svgPathWhite = "";
        let svgPathBlack = "";
        let svgDots = "";
        if (data.eval_graph && data.eval_graph.length > 0) {
            const width = 450;
            const height = 80;
            const step = width / (data.eval_graph.length - 1 || 1);
            
            let pts = [];
            data.eval_graph.forEach((point, i) => {
                let e = point.eval;
                if (e > 10) e = 10;
                if (e < -10) e = -10;
                // Map -10..10 to height..0
                const y = height - ((e + 10) / 20) * height;
                const x = i * step;
                pts.push({x, y, eval: point.eval});
            });

            const pointsStr = pts.map(p => `${p.x},${p.y}`).join(" ");
            
            // White Area (top to graph line)
            svgPathWhite = `0,0 ${pointsStr} ${width},0`;
            
            // Black Area (graph line to bottom)
            svgPathBlack = `0,${height} ${pointsStr} ${width},${height}`;
            
            // Just simple points to make it look active
            pts.forEach((p, i) => {
                if(i > 0 && i % 2 === 0 && i < pts.length -1) {
                    const color = p.y < height/2 ? '#fff' : '#000';
                    svgDots += `<circle cx="${p.x}" cy="${p.y}" r="3" fill="${color}" stroke="#888" stroke-width="1"/>`;
                }
            });
        }

        // 2. Populate Modal (Coach section is empty initially, populated by summary button)
        let html = `
            <!-- Coach Section (Injected later) -->
            <div id="coachSummaryContainer"></div>

            <!-- Graph Section -->
            <div class="w-full h-[80px] bg-gray-600 relative overflow-hidden flex-shrink-0">
                <svg width="100%" height="100%" viewBox="0 0 450 80" preserveAspectRatio="none">
                    <polygon points="${svgPathWhite}" fill="#e3e3e3" />
                    <polygon points="${svgPathBlack}" fill="#3b3936" />
                    <line x1="0" y1="40" x2="450" y2="40" stroke="#888" stroke-width="1" />
                    ${svgDots}
                </svg>
            </div>

            <!-- Players & Accuracy -->
            <div class="p-6">
                <div class="flex justify-center items-center gap-16 mb-8">
                    <!-- White -->
                    <div class="flex flex-col items-center">
                        <div class="text-sm font-bold text-gray-300 mb-2">White</div>
                        <div class="w-14 h-14 bg-gray-200 rounded flex items-center justify-center mb-2 shadow-inner border border-gray-400">
                            <img src="/static/pieces/neo/wP.png" class="w-10 h-10">
                        </div>
                        <div class="bg-white text-black font-bold text-xl px-3 py-1 rounded w-20 text-center shadow-sm">
                            ${data.players.white.accuracy}
                        </div>
                    </div>
                    
                    <!-- Black -->
                    <div class="flex flex-col items-center">
                        <div class="text-sm font-bold text-gray-300 mb-2">Black</div>
                        <div class="w-14 h-14 bg-[#262421] rounded flex items-center justify-center mb-2 shadow-inner border-2 border-green-500">
                            <img src="/static/pieces/neo/bP.png" class="w-10 h-10">
                        </div>
                        <div class="bg-gray-800 text-white font-bold text-xl px-3 py-1 rounded w-20 text-center shadow-sm">
                            ${data.players.black.accuracy}
                        </div>
                    </div>
                </div>

                <!-- Stats Breakdown -->
                <div class="space-y-3 px-8 text-sm font-bold text-gray-300">
                    <div class="flex justify-between items-center">
                        <div class="w-1/3">Brilliant</div>
                        <div class="w-1/3 flex justify-center gap-4">
                            <span class="text-[#1baca6] w-4 text-right">${data.players.white.brilliant}</span>
                            <span class="bg-[#1baca6] text-white text-xs px-1.5 py-0.5 rounded">!!</span>
                            <span class="text-[#1baca6] w-4 text-left">${data.players.black.brilliant}</span>
                        </div>
                        <div class="w-1/3 text-right"></div>
                    </div>
                    
                    <div class="flex justify-between items-center">
                        <div class="w-1/3">Great</div>
                        <div class="w-1/3 flex justify-center gap-4">
                            <span class="text-[#5c8bb0] w-4 text-right">${data.players.white.great}</span>
                            <span class="bg-[#5c8bb0] text-white text-xs px-2 py-0.5 rounded">!</span>
                            <span class="text-[#5c8bb0] w-4 text-left">${data.players.black.great}</span>
                        </div>
                        <div class="w-1/3"></div>
                    </div>
                    
                    <div class="flex justify-between items-center">
                        <div class="w-1/3">Best</div>
                        <div class="w-1/3 flex justify-center gap-4">
                            <span class="text-[#81b64c] w-4 text-right">${data.players.white.best}</span>
                            <span class="bg-[#81b64c] text-white text-xs px-1 py-0.5 rounded">★</span>
                            <span class="text-[#81b64c] w-4 text-left">${data.players.black.best}</span>
                        </div>
                        <div class="w-1/3"></div>
                    </div>
                    
                    <div class="flex justify-between items-center">
                        <div class="w-1/3">Mistake</div>
                        <div class="w-1/3 flex justify-center gap-4">
                            <span class="text-[#ffa400] w-4 text-right">${data.players.white.mistake}</span>
                            <span class="bg-[#ffa400] text-white text-xs px-1.5 py-0.5 rounded">?</span>
                            <span class="text-[#ffa400] w-4 text-left">${data.players.black.mistake}</span>
                        </div>
                        <div class="w-1/3"></div>
                    </div>
                    
                    <div class="flex justify-between items-center">
                        <div class="w-1/3">Miss</div>
                        <div class="w-1/3 flex justify-center gap-4">
                            <span class="text-[#ff7769] w-4 text-right">${data.players.white.miss}</span>
                            <span class="bg-[#ff7769] text-white text-xs px-1.5 py-0.5 rounded">✖</span>
                            <span class="text-[#ff7769] w-4 text-left">${data.players.black.miss}</span>
                        </div>
                        <div class="w-1/3"></div>
                    </div>
                    
                    <div class="flex justify-between items-center">
                        <div class="w-1/3">Blunder</div>
                        <div class="w-1/3 flex justify-center gap-4">
                            <span class="text-[#fa412d] w-4 text-right">${data.players.white.blunder}</span>
                            <span class="bg-[#fa412d] text-white text-xs px-1 py-0.5 rounded">??</span>
                            <span class="text-[#fa412d] w-4 text-left">${data.players.black.blunder}</span>
                        </div>
                        <div class="w-1/3"></div>
                    </div>
            </div>
        `;
        $('#reviewContent').html(html);

        // Color Code Moves in Grid
        data.moves.forEach((move, i) => {
            const rowIdx = Math.floor(i / 2);
            const isWhite = (i % 2) === 0;
            const row = $(`.move-row[data-idx="${rowIdx}"]`);
            const input = isWhite ? row.find('.move-white input') : row.find('.move-black input');
            
            // Remove previous classifications and default validation colors
            input.removeClass('text-red-400 text-yellow-400 text-green-400 text-purple-400 text-green-300 text-gray-200 text-gray-300 font-bold');
            
            if (move.classification === 'blunder' || move.classification === 'miss') {
                input.addClass('text-red-400 font-bold');
            } else if (move.classification === 'mistake' || move.classification === 'inaccuracy') {
                input.addClass('text-yellow-400 font-bold');
            } else if (['best', 'great', 'brilliant', 'excellent', 'good'].includes(move.classification)) {
                input.addClass('text-green-400 font-bold');
            } else {
                // Fallback for any unknown classification
                input.addClass('text-gray-300 font-bold');
            }
        });

    } catch (e) {
        $('#reviewContent').html(`<div class="text-red-400 text-center py-4">Error: ${e.message}</div>`);
    }
}

// -- Decoupled Summary Endpoint --
async function handleReviewSummary() {
    if (!gameState.game_id) {
        alert("Please save the game first!");
        return;
    }

    const originalHtml = $('#summaryBtn').html();
    $('#summaryBtn').html('<span>Generating Coaching Summary...</span>').prop('disabled', true);
    $('#reviewModal').removeClass('hidden'); // Ensure modal is open
    $('#coachSummaryContainer').removeClass('hidden').html(`
        <div class="flex justify-center p-6 bg-[#312e2b]">
            <div class="text-gray-400 italic">Asking Coach AI for summary...</div>
        </div>
    `);

    try {
        const res = await fetch(`${API_BASE}/api/review-summary`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify({ game_id: gameState.game_id })
        });

        if (!res.ok) throw new Error("Failed to generate summary");

        const data = await res.json();
        
        // Inject the Coach UI
        const coachHtml = `
            <div class="flex items-start gap-4 p-6 bg-[#312e2b]">
                <div class="w-16 h-16 shrink-0 bg-gray-600 rounded-full flex items-center justify-center text-3xl overflow-hidden border-2 border-gray-500">
                    🧑🏾‍🏫
                </div>
                <div class="bg-white text-gray-900 p-4 rounded-xl rounded-tl-none relative text-sm shadow-md font-semibold w-full">
                    <div class="absolute -left-3 top-0 w-4 h-4 bg-white" style="clip-path: polygon(100% 0, 0 0, 100% 100%);"></div>
                    ${data.summary}
                </div>
            </div>
        `;
        $('#coachSummaryContainer').html(coachHtml);
    } catch (e) {
        $('#coachSummaryContainer').html(`<div class="text-red-400 text-center py-4">Error: ${e.message}</div>`);
    } finally {
        $('#summaryBtn').html(originalHtml).prop('disabled', false);
    }
}
