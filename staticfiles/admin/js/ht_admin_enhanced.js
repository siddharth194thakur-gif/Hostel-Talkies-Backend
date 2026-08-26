/**
 * HostelTalkies Admin UI Enhancement Engine
 * Notion / Linear / Apple inspired modern UX for Django Admin
 * Author: HostelTalkies Team
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    initActionToolbar();
    initHorizontalFilters();
    initDragAndDropUploads();
    initKeyboardShortcuts();
    initModalConfirmations();
  });

  /* ==========================================================================
     1. Modern Action Toolbar & Multi-Select Handler
     ========================================================================== */
  function initActionToolbar() {
    const actionSelect = document.querySelector('select[name="action"]');
    const selectAcross = document.querySelector('input.select-across');
    const selectAllBtn = document.getElementById('ht-select-all-btn');
    const countDisplay = document.getElementById('ht-selection-count');
    const pill = document.getElementById('ht-selection-pill');
    const nativeWrap = document.querySelector('.ht-native-action-wrap');
    const actionTable = document.querySelector('#result_list');
    const actionAllCheckbox = document.querySelector('#action-toggle');

    if (!actionTable) return;

    const rowCheckboxes = actionTable.querySelectorAll('input.action-select');

    function updateSelectionState() {
      let selectedCount = 0;
      rowCheckboxes.forEach(function (cb) {
        const row = cb.closest('tr');
        if (cb.checked) {
          selectedCount++;
          if (row) row.classList.add('ht-row-selected');
        } else {
          if (row) row.classList.remove('ht-row-selected');
        }
      });

      if (countDisplay) {
        countDisplay.textContent = selectedCount;
      }

      if (pill) {
        if (selectedCount > 0) {
          pill.classList.add('ht-has-selection');
        } else {
          pill.classList.remove('ht-has-selection');
        }
      }

      if (selectAllBtn) {
        if (selectedCount === rowCheckboxes.length && rowCheckboxes.length > 0) {
          selectAllBtn.textContent = 'Deselect All';
        } else {
          selectAllBtn.textContent = 'Select All';
        }
      }
    }

    rowCheckboxes.forEach(function (cb) {
      cb.addEventListener('change', updateSelectionState);
    });

    if (actionAllCheckbox) {
      actionAllCheckbox.addEventListener('change', function () {
        setTimeout(updateSelectionState, 50);
      });
    }

    if (selectAllBtn) {
      selectAllBtn.addEventListener('click', function () {
        const allSelected = Array.from(rowCheckboxes).every(cb => cb.checked);
        rowCheckboxes.forEach(cb => {
          cb.checked = !allSelected;
        });
        if (actionAllCheckbox) {
          actionAllCheckbox.checked = !allSelected;
        }
        updateSelectionState();
      });
    }

    // Initial state check
    updateSelectionState();
  }

  /* ==========================================================================
     2. Horizontal Filter Dropdown Controller
     ========================================================================== */
  function initHorizontalFilters() {
    const filterGroups = document.querySelectorAll('.ht-filter-group');
    if (!filterGroups.length) return;

    filterGroups.forEach(function (group) {
      const trigger = group.querySelector('.ht-filter-trigger');
      const menu = group.querySelector('.ht-filter-dropdown-menu');

      if (!trigger || !menu) return;

      trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        const isOpen = group.classList.contains('open');

        // Close all other open filters
        filterGroups.forEach(g => {
          if (g !== group) g.classList.remove('open');
        });

        if (isOpen) {
          group.classList.remove('open');
          trigger.setAttribute('aria-expanded', 'false');
        } else {
          group.classList.add('open');
          trigger.setAttribute('aria-expanded', 'true');
        }
      });
    });

    // Close on outside click
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.ht-filter-group')) {
        filterGroups.forEach(g => g.classList.remove('open'));
      }
    });
  }

  /* ==========================================================================
     3. Modern Drag & Drop PDF & File Upload Widget
     ========================================================================== */
  function initDragAndDropUploads() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    if (!fileInputs.length) return;

    fileInputs.forEach(function (input) {
      // Don't re-wrap if already processed
      if (input.dataset.htEnhanced) return;
      input.dataset.htEnhanced = 'true';

      const fieldBox = input.closest('.ht-field-control-wrap') || input.parentElement;
      const isPdfField = input.name.includes('file') || input.name.includes('pdf') || input.name.includes('attachment');

      // Create Dropzone Container
      const dropzone = document.createElement('div');
      dropzone.className = 'ht-dropzone-container';

      // Check if there is an existing file (Django file field initial display)
      const existingLink = fieldBox.querySelector('a');
      let existingFileName = '';
      let existingFileUrl = '';
      if (existingLink && existingLink.href) {
        existingFileName = existingLink.textContent.trim() || 'Existing Attached File';
        existingFileUrl = existingLink.href;
      }

      dropzone.innerHTML = `
        <div class="ht-dropzone-area" id="dropzone-${input.name}">
          <div class="ht-dropzone-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
          </div>
          <div class="ht-dropzone-text">
            <span class="ht-dropzone-title">Drag & Drop your ${isPdfField ? 'PDF Document' : 'File'} here</span>
            <span class="ht-dropzone-sub">or <button type="button" class="ht-dropzone-browse-btn">Browse Files</button></span>
          </div>
          <div class="ht-dropzone-hint">Supported format: ${isPdfField ? 'PDF documents up to 50MB' : 'PDF, JPG, PNG, DOCX'}</div>
        </div>

        <div class="ht-file-preview-card" style="display: ${existingFileName ? 'flex' : 'none'};">
          <div class="ht-file-preview-icon">📄</div>
          <div class="ht-file-preview-info">
            <div class="ht-file-name" title="${existingFileName}">${existingFileName || 'No file selected'}</div>
            <div class="ht-file-meta">
              <span class="ht-file-size">${existingFileUrl ? 'Uploaded on Server' : 'Ready to upload'}</span>
              ${existingFileUrl ? `<a href="${existingFileUrl}" target="_blank" class="ht-file-view-link">View File ↗</a>` : ''}
            </div>
          </div>
          <div class="ht-file-preview-actions">
            <button type="button" class="ht-btn-replace-file" title="Choose a different file">Replace</button>
            <button type="button" class="ht-btn-remove-file" title="Remove file">✕</button>
          </div>
        </div>

        <div class="ht-upload-alert" style="display:none;"></div>
      `;

      // Insert dropzone before input and hide default input
      input.style.display = 'none';
      fieldBox.insertBefore(dropzone, input);

      const dropArea = dropzone.querySelector('.ht-dropzone-area');
      const browseBtn = dropzone.querySelector('.ht-dropzone-browse-btn');
      const previewCard = dropzone.querySelector('.ht-file-preview-card');
      const fileNameEl = dropzone.querySelector('.ht-file-name');
      const fileSizeEl = dropzone.querySelector('.ht-file-size');
      const replaceBtn = dropzone.querySelector('.ht-btn-replace-file');
      const removeBtn = dropzone.querySelector('.ht-btn-remove-file');
      const alertEl = dropzone.querySelector('.ht-upload-alert');

      function formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
      }

      function handleFileSelected(file) {
        if (!file) return;

        // PDF Validation for Study Notes & Documents
        if (isPdfField && !file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
          alertEl.textContent = '⚠️ Please upload a valid PDF document (.pdf format).';
          alertEl.style.display = 'block';
          alertEl.className = 'ht-upload-alert ht-upload-alert-warning';
          return;
        }

        alertEl.style.display = 'none';
        fileNameEl.textContent = file.name;
        fileSizeEl.textContent = formatFileSize(file.size);
        
        dropArea.style.display = 'none';
        previewCard.style.display = 'flex';
      }

      // Drag & Drop events
      ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, function (e) {
          e.preventDefault();
          e.stopPropagation();
          dropArea.classList.add('drag-over');
        });
      });

      ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, function (e) {
          e.preventDefault();
          e.stopPropagation();
          dropArea.classList.remove('drag-over');
        });
      });

      dropArea.addEventListener('drop', function (e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length) {
          input.files = files;
          handleFileSelected(files[0]);
        }
      });

      dropArea.addEventListener('click', function () {
        input.click();
      });

      browseBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        input.click();
      });

      replaceBtn.addEventListener('click', function () {
        input.click();
      });

      removeBtn.addEventListener('click', function () {
        input.value = '';
        previewCard.style.display = 'none';
        dropArea.style.display = 'flex';
        alertEl.style.display = 'none';

        // Check if there is a clear checkbox for Django
        const clearCheckbox = fieldBox.querySelector('input[type="checkbox"][name$="-clear"]');
        if (clearCheckbox) {
          clearCheckbox.checked = true;
        }
      });

      input.addEventListener('change', function () {
        if (input.files && input.files.length) {
          handleFileSelected(input.files[0]);
        }
      });
    });
  }

  /* ==========================================================================
     4. Action Confirmation Modal
     ========================================================================== */
  function initModalConfirmations() {
    const modal = document.getElementById('ht-confirm-modal');
    const modalTitle = document.getElementById('ht-modal-title');
    const modalDesc = document.getElementById('ht-modal-desc');
    const modalIcon = document.getElementById('ht-modal-icon');
    const confirmBtn = document.getElementById('ht-modal-confirm');
    const cancelBtn = document.getElementById('ht-modal-cancel');
    const actionForm = document.getElementById('changelist-form');
    const actionSelect = document.querySelector('select[name="action"]');
    const goBtn = document.getElementById('ht-action-go-btn');

    if (!modal || !actionForm || !goBtn || !actionSelect) return;

    let pendingSubmit = false;

    goBtn.addEventListener('click', function (e) {
      const selectedAction = actionSelect.value;
      const selectedCheckboxes = document.querySelectorAll('input.action-select:checked');

      if (!selectedAction || selectedCheckboxes.length === 0) {
        // Let normal browser validation or Django handle empty action
        return;
      }

      if (pendingSubmit) return;

      e.preventDefault();

      const actionText = actionSelect.options[actionSelect.selectedIndex].text;
      const isDestructive = selectedAction.includes('delete') || selectedAction.includes('block') || selectedAction.includes('deactivate');

      modalTitle.textContent = isDestructive ? '⚠️ Confirm Action' : 'Confirm Bulk Action';
      modalDesc.textContent = `Are you sure you want to perform "${actionText}" on ${selectedCheckboxes.length} selected item(s)?`;
      modalIcon.textContent = isDestructive ? '🗑️' : '✨';

      if (isDestructive) {
        confirmBtn.className = 'ht-modal-btn ht-modal-btn-danger';
        confirmBtn.textContent = 'Yes, Proceed';
      } else {
        confirmBtn.className = 'ht-modal-btn ht-modal-btn-confirm';
        confirmBtn.textContent = 'Apply Action';
      }

      modal.style.display = 'flex';

      function onConfirm() {
        modal.style.display = 'none';
        pendingSubmit = true;
        goBtn.click();
      }

      function onCancel() {
        modal.style.display = 'none';
        confirmBtn.removeEventListener('click', onConfirm);
        cancelBtn.removeEventListener('click', onCancel);
      }

      confirmBtn.onclick = onConfirm;
      cancelBtn.onclick = onCancel;
    });

    // Close modal on backdrop click
    modal.addEventListener('click', function (e) {
      if (e.target === modal) {
        modal.style.display = 'none';
      }
    });
  }

  /* ==========================================================================
     5. Keyboard Shortcuts
     ========================================================================== */
  function initKeyboardShortcuts() {
    document.addEventListener('keydown', function (e) {
      // Focus search on '/' when not in an input
      if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
        const searchInput = document.getElementById('searchbar');
        if (searchInput) {
          e.preventDefault();
          searchInput.focus();
          searchInput.select();
        }
      }

      // Close modal on Esc
      if (e.key === 'Escape') {
        const modal = document.getElementById('ht-confirm-modal');
        if (modal && modal.style.display !== 'none') {
          modal.style.display = 'none';
        }
        const filterGroups = document.querySelectorAll('.ht-filter-group.open');
        filterGroups.forEach(g => g.classList.remove('open'));
      }
    });
  }

})();
