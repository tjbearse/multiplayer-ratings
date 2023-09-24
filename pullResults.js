Array.from(document.querySelectorAll(".score-summary-row")).map((r) => ({
	rank: parseInt(r.querySelector(".score-fieldset-rank").textContent),
	player: r.querySelector(".score-content-title").textContent.trim(),
}));
