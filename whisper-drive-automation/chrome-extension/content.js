/**
 * Content Script pour l'extension Marqueur Segments Vidéo
 * Injecte une barre d'outils flottante dans Google Docs
 */

// Vérifier qu'on est sur un Google Doc
if (window.location.href.includes('docs.google.com/document')) {
  console.log('🎬 Extension Marqueur Segments chargée');

  // Attendre que le document soit prêt
  setTimeout(initExtension, 2000);
}

function initExtension() {
  // Vérifier si l'extension n'est pas déjà injectée
  if (document.getElementById('video-segment-marker-toolbar')) {
    return;
  }

  createToolbar();
  console.log('✅ Barre d\'outils créée');
}

/**
 * Crée la barre d'outils flottante
 */
function createToolbar() {
  const toolbar = document.createElement('div');
  toolbar.id = 'video-segment-marker-toolbar';
  toolbar.className = 'vsm-toolbar';

  toolbar.innerHTML = `
    <div class="vsm-header">
      <span class="vsm-title">🎬 Extraits Vidéo</span>
      <button class="vsm-toggle" id="vsm-toggle">−</button>
    </div>
    <div class="vsm-content" id="vsm-content">
      <div class="vsm-section">
        <div class="vsm-section-title">Segments rapides</div>
        <div class="vsm-button-grid">
          ${[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n =>
            `<button class="vsm-btn vsm-btn-segment" data-segment="S${n}">S${n}</button>`
          ).join('')}
        </div>
      </div>

      <div class="vsm-section">
        <div class="vsm-section-title">Actions</div>
        <button class="vsm-btn vsm-btn-action" id="vsm-custom">✏️ Segment personnalisé</button>
        <button class="vsm-btn vsm-btn-action" id="vsm-list">📋 Lister les segments</button>
        <button class="vsm-btn vsm-btn-action" id="vsm-remove">🗑️ Retirer les marqueurs</button>
      </div>

      <div class="vsm-section">
        <div class="vsm-section-title">Finition</div>
        <button class="vsm-btn vsm-btn-ready" id="vsm-ready">✅ Marquer comme PRÊT</button>
        <button class="vsm-btn vsm-btn-action" id="vsm-status">📊 Vérifier le statut</button>
      </div>
    </div>
  `;

  document.body.appendChild(toolbar);

  // Ajouter les event listeners
  attachEventListeners();

  // Rendre la toolbar draggable
  makeDraggable(toolbar);
}

/**
 * Attache les event listeners aux boutons
 */
function attachEventListeners() {
  // Toggle toolbar
  document.getElementById('vsm-toggle').addEventListener('click', toggleToolbar);

  // Boutons de segments (S1-S10)
  document.querySelectorAll('.vsm-btn-segment').forEach(btn => {
    btn.addEventListener('click', () => {
      const segment = btn.dataset.segment;
      markSegment(segment);
    });
  });

  // Segment personnalisé
  document.getElementById('vsm-custom').addEventListener('click', markCustomSegment);

  // Lister les segments
  document.getElementById('vsm-list').addEventListener('click', listSegments);

  // Retirer les marqueurs
  document.getElementById('vsm-remove').addEventListener('click', removeMarkers);

  // Marquer comme prêt
  document.getElementById('vsm-ready').addEventListener('click', markAsReady);

  // Vérifier le statut
  document.getElementById('vsm-status').addEventListener('click', checkStatus);
}

/**
 * Toggle la toolbar (expand/collapse)
 */
function toggleToolbar() {
  const content = document.getElementById('vsm-content');
  const toggle = document.getElementById('vsm-toggle');

  if (content.style.display === 'none') {
    content.style.display = 'block';
    toggle.textContent = '−';
  } else {
    content.style.display = 'none';
    toggle.textContent = '+';
  }
}

/**
 * Rend la toolbar draggable
 */
function makeDraggable(element) {
  let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
  const header = element.querySelector('.vsm-header');

  header.onmousedown = dragMouseDown;

  function dragMouseDown(e) {
    e.preventDefault();
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    document.onmousemove = elementDrag;
  }

  function elementDrag(e) {
    e.preventDefault();
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    element.style.top = (element.offsetTop - pos2) + 'px';
    element.style.left = (element.offsetLeft - pos1) + 'px';
  }

  function closeDragElement() {
    document.onmouseup = null;
    document.onmousemove = null;
  }
}

/**
 * Marque un segment dans le document
 */
function markSegment(segmentCode) {
  const selection = window.getSelection();

  if (!selection || selection.rangeCount === 0) {
    showNotification('⚠️ Veuillez sélectionner du texte à marquer', 'warning');
    return;
  }

  const range = selection.getRangeAt(0);
  const selectedText = range.toString();

  if (!selectedText.trim()) {
    showNotification('⚠️ Aucun texte sélectionné', 'warning');
    return;
  }

  try {
    // Créer le texte avec les balises
    const markedText = `🎬 ${segmentCode} 🎬\n${selectedText}\n🎬 /${segmentCode} 🎬`;

    // Remplacer la sélection
    range.deleteContents();
    const textNode = document.createTextNode(markedText);
    range.insertNode(textNode);

    // Déselectionner
    selection.removeAllRanges();

    showNotification(`✅ Segment ${segmentCode} marqué avec succès!`, 'success');
  } catch (error) {
    console.error('Erreur lors du marquage:', error);
    showNotification('❌ Erreur lors du marquage. Utilisez le menu Apps Script à la place.', 'error');
  }
}

/**
 * Marque un segment personnalisé
 */
function markCustomSegment() {
  const segmentCode = prompt('Entrez le code du segment (ex: S11, S20, etc.):');

  if (!segmentCode) {
    return;
  }

  const code = segmentCode.trim().toUpperCase();

  // Vérifier le format
  if (!/^S\d+$/.test(code)) {
    showNotification('⚠️ Format invalide. Utilisez le format S1, S2, S11, etc.', 'warning');
    return;
  }

  markSegment(code);
}

/**
 * Liste tous les segments du document
 */
function listSegments() {
  // Récupérer le contenu du document (difficile avec Google Docs API)
  // Pour simplifier, on utilise une approche alternative
  showNotification('💡 Utilisez Ctrl+F pour chercher "🎬 S" et voir tous les segments', 'info');
}

/**
 * Retire tous les marqueurs du document
 */
function removeMarkers() {
  const confirmed = confirm('Êtes-vous sûr de vouloir retirer TOUS les marqueurs du document?');

  if (!confirmed) {
    return;
  }

  showNotification('⚠️ Utilisez le menu Apps Script pour retirer les marqueurs de manière sûre', 'warning');
}

/**
 * Marque le document comme prêt pour le découpage
 */
function markAsReady() {
  try {
    // Créer un range à la fin du document
    const selection = window.getSelection();
    selection.removeAllRanges();

    // Insérer la balise READY à la fin
    const readyMarker = '\n\n🎬 READY 🎬\n';

    // Note: L'insertion à la fin du document est complexe avec Google Docs
    // On copie le marqueur dans le presse-papiers pour que l'utilisateur le colle
    navigator.clipboard.writeText(readyMarker).then(() => {
      showNotification('✅ Balise READY copiée! Collez-la à la fin du document (Ctrl+V)', 'success');
    }).catch(() => {
      showNotification('💡 Copiez cette balise à la fin du document: 🎬 READY 🎬', 'info');
    });
  } catch (error) {
    console.error('Erreur:', error);
    showNotification('💡 Ajoutez cette balise à la fin du document: 🎬 READY 🎬', 'info');
  }
}

/**
 * Vérifie le statut du document
 */
function checkStatus() {
  showNotification('💡 Utilisez le menu Apps Script pour voir le statut détaillé', 'info');
}

/**
 * Affiche une notification
 */
function showNotification(message, type = 'info') {
  // Supprimer les notifications existantes
  const existing = document.querySelectorAll('.vsm-notification');
  existing.forEach(n => n.remove());

  // Créer la notification
  const notification = document.createElement('div');
  notification.className = `vsm-notification vsm-notification-${type}`;
  notification.textContent = message;

  document.body.appendChild(notification);

  // Retirer après 3 secondes
  setTimeout(() => {
    notification.style.opacity = '0';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Réinjecter l'extension si la page change (Google Docs est une SPA)
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    if (url.includes('docs.google.com/document')) {
      setTimeout(initExtension, 2000);
    }
  }
}).observe(document, {subtree: true, childList: true});
