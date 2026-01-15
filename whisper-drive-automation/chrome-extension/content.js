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
 * Extrait l'ID du document depuis l'URL
 */
function getDocumentId() {
  const match = window.location.href.match(/\/document\/d\/([a-zA-Z0-9-_]+)/);
  return match ? match[1] : null;
}

/**
 * Marque un segment dans le document via l'API Google Docs
 */
async function markSegment(segmentCode) {
  // Afficher un message pour guider l'utilisateur
  showNotification(`📋 Pour marquer ${segmentCode}: 1) Sélectionnez le texte 2) Copiez (Ctrl/Cmd+C) 3) Cliquez à nouveau sur ${segmentCode}`, 'info', 7000);

  let selectedText = '';

  try {
    // Lire le texte du clipboard (l'utilisateur doit avoir copié avec Ctrl+C)
    selectedText = await navigator.clipboard.readText();
    console.log('Texte lu du clipboard:', selectedText);
    console.log('Longueur du texte:', selectedText ? selectedText.length : 0);

  } catch (error) {
    console.error('Erreur lecture clipboard:', error);
    showNotification('❌ Impossible de lire le clipboard. Autorisez l\'accès au clipboard.', 'error');
    return;
  }

  if (!selectedText || !selectedText.trim()) {
    showNotification('⚠️ Clipboard vide. Copiez d\'abord le texte (Ctrl/Cmd+C) puis réessayez.', 'warning', 5000);
    console.log('selectedText est vide ou null');
    return;
  }

  selectedText = selectedText.trim();
  console.log('Texte copié:', selectedText);

  // Vérifier si le texte contient déjà des balises (ex: 🎬 S1 🎬)
  const contentMatch = selectedText.match(/🎬\s*S\d+\s*🎬\n?(.*?)\n?🎬\s*\/S\d+\s*🎬/s);

  let textToSearch = selectedText; // Le texte complet à chercher dans le document
  let contentOnly = selectedText;  // Le contenu seul (sans balises) pour créer la nouvelle version

  if (contentMatch && contentMatch[1]) {
    // Le texte a déjà des balises
    console.log('Texte déjà marqué détecté, remplacement des balises...');
    contentOnly = contentMatch[1].trim();
    // On cherche le texte COMPLET avec les anciennes balises
    textToSearch = selectedText;
    console.log('Contenu seul:', contentOnly);
    console.log('Texte complet à chercher:', textToSearch);
    showNotification(`🔄 Remplacement du marqueur par ${segmentCode}...`, 'info');
  } else {
    // Pas de balises, c'est un nouveau marquage
    console.log('Nouveau marquage');
    contentOnly = selectedText;
    textToSearch = selectedText;
    showNotification('⏳ Insertion en cours...', 'info');
  }

  // Extraire l'ID du document
  const documentId = getDocumentId();
  if (!documentId) {
    showNotification('❌ Impossible d\'obtenir l\'ID du document', 'error');
    return;
  }

  try {
    // Récupérer le document via l'API
    const docResponse = await chrome.runtime.sendMessage({
      action: 'getDocContent',
      documentId: documentId
    });

    if (!docResponse.success) {
      throw new Error(docResponse.error);
    }

    const doc = docResponse.doc;

    // Construire tout le texte du document avec les indices
    let fullText = '';
    let indexMap = []; // Map pour retrouver l'index réel depuis l'index dans fullText
    const content = doc.body.content;

    for (let i = 0; i < content.length; i++) {
      const element = content[i];
      if (element.paragraph) {
        for (let j = 0; j < element.paragraph.elements.length; j++) {
          const textRun = element.paragraph.elements[j];
          if (textRun.textRun && textRun.textRun.content) {
            const text = textRun.textRun.content;
            const startIndex = textRun.startIndex;

            // Ajouter chaque caractère avec son index réel
            for (let k = 0; k < text.length; k++) {
              fullText += text[k];
              indexMap.push(startIndex + k);
            }
          }
        }
      }
    }

    // Chercher le texte directement dans fullText (sans normalisation pour éviter les problèmes d'indices)
    const foundPosition = fullText.indexOf(textToSearch);

    if (foundPosition === -1) {
      // Essayer avec normalisation des espaces si la recherche exacte échoue
      const normalizedFullText = fullText.replace(/\s+/g, ' ').trim();
      const normalizedSearchText = textToSearch.replace(/\s+/g, ' ').trim();
      const normalizedPosition = normalizedFullText.indexOf(normalizedSearchText);

      if (normalizedPosition === -1) {
        showNotification('❌ Texte non trouvé. Le texte a peut-être été modifié. Réessayez.', 'error');
        console.log('Texte recherché:', textToSearch);
        console.log('Texte document (début):', fullText.substring(0, 500));
        return;
      }

      showNotification('⚠️ Impossible de trouver le texte exactement. Vérifiez manuellement.', 'warning');
      return;
    }

    // Retrouver les vrais indices dans le document
    const foundIndex = indexMap[foundPosition];
    const foundEndPosition = foundPosition + textToSearch.length - 1;
    const foundEndIndex = indexMap[foundEndPosition];

    console.log('Position trouvée:', foundPosition);
    console.log('Index document:', foundIndex, 'à', foundEndIndex);

    // Créer le texte avec les balises (utiliser contentOnly, pas textToSearch)
    const markedText = `🎬 ${segmentCode} 🎬\n${contentOnly}\n🎬 /${segmentCode} 🎬`;

    // Remplacer le texte via l'API
    const replaceResponse = await chrome.runtime.sendMessage({
      action: 'replaceText',
      documentId: documentId,
      startIndex: foundIndex,
      endIndex: foundEndIndex + 1, // +1 car endIndex est exclusif dans l'API
      newText: markedText
    });

    if (!replaceResponse.success) {
      throw new Error(replaceResponse.error);
    }

    showNotification(`✅ Segment ${segmentCode} marqué avec succès!`, 'success');
  } catch (error) {
    console.error('Erreur lors du marquage:', error);
    showNotification(`❌ Erreur: ${error.message}`, 'error');
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
 * Marque le document comme prêt pour le découpage via l'API
 */
async function markAsReady() {
  // Extraire l'ID du document
  const documentId = getDocumentId();
  if (!documentId) {
    showNotification('❌ Impossible d\'obtenir l\'ID du document', 'error');
    return;
  }

  showNotification('⏳ Ajout de la balise READY...', 'info');

  try {
    // Insérer la balise READY à la fin
    const readyMarker = '\n\n🎬 READY 🎬\n';

    const response = await chrome.runtime.sendMessage({
      action: 'insertTextAtEnd',
      documentId: documentId,
      text: readyMarker
    });

    if (!response.success) {
      throw new Error(response.error);
    }

    showNotification('✅ Document marqué comme PRÊT! Le traitement va commencer automatiquement.', 'success');
  } catch (error) {
    console.error('Erreur:', error);
    showNotification(`❌ Erreur: ${error.message}`, 'error');
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
function showNotification(message, type = 'info', duration = 3000) {
  // Supprimer les notifications existantes
  const existing = document.querySelectorAll('.vsm-notification');
  existing.forEach(n => n.remove());

  // Créer la notification
  const notification = document.createElement('div');
  notification.className = `vsm-notification vsm-notification-${type}`;
  notification.textContent = message;

  document.body.appendChild(notification);

  // Retirer après la durée spécifiée
  setTimeout(() => {
    notification.style.opacity = '0';
    setTimeout(() => notification.remove(), 300);
  }, duration);
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
