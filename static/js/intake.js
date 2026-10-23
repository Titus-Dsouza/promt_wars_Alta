/**
 * MediScribe — Patient Intake & Gemma 4 AI Processing Engine (Phase 3)
 * Pure vanilla JavaScript with accessibility, keyboard navigation, and responsive validation.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const landingSection = document.getElementById('landing-section');
  const intakeContainer = document.getElementById('intake-container');
  const startIntakeBtn = document.getElementById('start-intake-btn');
  const tryDemoBtn = document.getElementById('try-demo-btn');
  const backBtn = document.getElementById('wizard-back-btn');
  const nextBtn = document.getElementById('wizard-next-btn');
  const progressFill = document.getElementById('progress-fill');
  const progressCount = document.getElementById('progress-count');
  const progressLabel = document.getElementById('progress-label');
  const alertBox = document.getElementById('intake-alert');
  const alertMessage = document.getElementById('alert-message');
  const loadingOverlay = document.getElementById('loading-overlay');
  const wizardFooter = document.getElementById('wizard-footer');
  const aiResultsStep = document.getElementById('ai-results-step');
  const aiBlockerStep = document.getElementById('ai-blocker-step');
  const aiEditBtn = document.getElementById('ai-edit-btn');
  const blockerEditBtn = document.getElementById('blocker-edit-btn');

  // Step elements
  const steps = [
    document.getElementById('step-1'),
    document.getElementById('step-2'),
    document.getElementById('step-3'),
    document.getElementById('step-4'),
  ];

  const stepLabels = [
    'Step 1: Primary Symptoms',
    'Step 2: Duration & Details',
    'Step 3: Medical Background',
    'Step 4: Review & Confirm',
  ];

  let currentStep = 0;
  let severityValue = 5;

  // Helper: Show Alert
  function showAlert(msg) {
    alertMessage.textContent = msg;
    alertBox.classList.add('active');
    alertBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function hideAlert() {
    alertBox.classList.remove('active');
  }

  // Navigation: Show Step
  function showStep(index) {
    hideAlert();
    if (aiResultsStep) aiResultsStep.classList.remove('active');
    if (aiBlockerStep) aiBlockerStep.classList.remove('active');

    steps.forEach((step, idx) => {
      if (step) {
        step.classList.toggle('active', idx === index);
      }
    });

    wizardFooter.style.display = 'flex';
    currentStep = index;
    const progressPercent = ((index + 1) / steps.length) * 100;
    progressFill.style.width = `${progressPercent}%`;
    progressCount.textContent = `Step ${index + 1} of ${steps.length}`;
    progressLabel.textContent = stepLabels[index];

    // Button states
    if (index === 0) {
      backBtn.disabled = true;
      backBtn.style.visibility = 'hidden';
      nextBtn.textContent = 'Continue';
    } else {
      backBtn.disabled = false;
      backBtn.style.visibility = 'visible';
      if (index === steps.length - 1) {
        nextBtn.textContent = 'Process with Google Gemma 4';
        populateReviewSummary();
      } else {
        nextBtn.textContent = 'Continue';
      }
    }

    intakeContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Switch to Intake View
  function openIntakeWizard() {
    landingSection.style.display = 'none';
    intakeContainer.style.display = 'block';
    intakeContainer.classList.add('active');
    showStep(0);
  }

  if (startIntakeBtn) {
    startIntakeBtn.addEventListener('click', openIntakeWizard);
  }

  // Demo Pre-fill Functionality
  if (tryDemoBtn) {
    tryDemoBtn.addEventListener('click', () => {
      openIntakeWizard();

      // Pre-select demo symptoms (Cough, Fever, Fatigue)
      const demoSymptoms = ['Persistent Cough', 'Fever or Chills', 'Fatigue / Weakness'];
      document.querySelectorAll('#step-1 .choice-card').forEach(card => {
        const title = card.querySelector('.choice-title')?.textContent.trim();
        if (demoSymptoms.includes(title)) {
          card.classList.add('selected');
          const input = card.querySelector('input');
          if (input) input.checked = true;
          card.setAttribute('aria-checked', 'true');
        }
      });

      // Duration: 2-3 days
      document.querySelectorAll('input[name="duration"]').forEach(radio => {
        if (radio.value === '2-3_days') {
          radio.checked = true;
          const parent = radio.closest('.choice-card');
          if (parent) {
            document.querySelectorAll('#duration-grid .choice-card').forEach(c => c.classList.remove('selected'));
            parent.classList.add('selected');
          }
        }
      });

      // Severity: 6
      severityValue = 6;
      document.querySelectorAll('.severity-btn').forEach(btn => {
        btn.classList.toggle('selected', btn.getAttribute('data-val') === '6');
      });
      const sevInput = document.getElementById('severity-input');
      if (sevInput) sevInput.value = '6';

      // Description
      const descInput = document.getElementById('symptom-description');
      if (descInput) {
        descInput.value =
          'Dry hacking cough starting 3 days ago. Mild fever around 100.4 F in the evenings. Experiencing persistent fatigue and chest tightness when coughing.';
      }

      // Medical History
      document.querySelectorAll('#step-3 .choice-card').forEach(card => {
        const title = card.querySelector('.choice-title')?.textContent.trim();
        if (title === 'Asthma / Respiratory') {
          card.classList.add('selected');
          const input = card.querySelector('input');
          if (input) input.checked = true;
        }
      });

      const medsInput = document.getElementById('current-medications');
      if (medsInput) medsInput.value = 'Albuterol inhaler as needed';

      const allergiesInput = document.getElementById('known-allergies');
      if (allergiesInput) allergiesInput.value = 'Penicillin (mild hives)';
    });
  }

  // Interactive Choice Cards (Keyboard & Click)
  document.querySelectorAll('.choice-card').forEach(card => {
    function toggleCard() {
      const input = card.querySelector('input');
      if (!input) return;

      if (input.type === 'checkbox') {
        input.checked = !input.checked;
        card.classList.toggle('selected', input.checked);
        card.setAttribute('aria-checked', input.checked ? 'true' : 'false');
      } else if (input.type === 'radio') {
        const name = input.name;
        document.querySelectorAll(`input[name="${name}"]`).forEach(r => {
          r.checked = false;
          const parent = r.closest('.choice-card');
          if (parent) {
            parent.classList.remove('selected');
            parent.setAttribute('aria-checked', 'false');
          }
        });
        input.checked = true;
        card.classList.add('selected');
        card.setAttribute('aria-checked', 'true');
      }
      hideAlert();
    }

    card.addEventListener('click', (e) => {
      if (e.target.tagName !== 'INPUT') {
        toggleCard();
      } else {
        card.classList.toggle('selected', e.target.checked);
      }
    });

    card.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        toggleCard();
      }
    });
  });

  // Severity Scale Controls
  document.querySelectorAll('.severity-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.severity-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      severityValue = parseInt(btn.getAttribute('data-val'), 10);
      const sevInput = document.getElementById('severity-input');
      if (sevInput) sevInput.value = severityValue;
    });
  });

  // Step Validation
  function validateCurrentStep() {
    if (currentStep === 0) {
      const selectedSymptoms = document.querySelectorAll('#step-1 input[type="checkbox"]:checked');
      const otherSymptom = document.getElementById('other-symptom')?.value.trim();
      if (selectedSymptoms.length === 0 && !otherSymptom) {
        showAlert('Please select at least one primary symptom or specify in the field below to continue.');
        return false;
      }
    } else if (currentStep === 1) {
      const durationSelected = document.querySelector('input[name="duration"]:checked');
      const description = document.getElementById('symptom-description')?.value.trim();
      if (!durationSelected) {
        showAlert('Please select approximate symptom duration.');
        return false;
      }
      if (!description || description.length < 10) {
        showAlert('Please provide a brief description of what you are experiencing (at least 10 characters).');
        return false;
      }
    }
    return true;
  }

  // Populate Review Summary (Step 4)
  function populateReviewSummary() {
    const symptoms = [];
    document.querySelectorAll('#step-1 input[type="checkbox"]:checked').forEach(cb => {
      symptoms.push(cb.value);
    });
    const otherSymptom = document.getElementById('other-symptom')?.value.trim();
    if (otherSymptom) symptoms.push(`Other: ${otherSymptom}`);

    const reviewSymptoms = document.getElementById('review-symptoms');
    if (reviewSymptoms) {
      reviewSymptoms.innerHTML = '';
      if (symptoms.length > 0) {
        symptoms.forEach(sym => {
          const span = document.createElement('span');
          span.className = 'review-tag';
          span.textContent = sym;
          reviewSymptoms.appendChild(span);
        });
      } else {
        reviewSymptoms.textContent = 'None reported';
      }
    }

    const durationInput = document.querySelector('input[name="duration"]:checked');
    const reviewDuration = document.getElementById('review-duration');
    if (reviewDuration) {
      reviewDuration.textContent = durationInput ? durationInput.value.replace('_', ' ') : 'Not specified';
    }

    const reviewSeverity = document.getElementById('review-severity');
    if (reviewSeverity) {
      reviewSeverity.textContent = `${severityValue} / 10`;
    }

    const desc = document.getElementById('symptom-description')?.value.trim();
    const reviewDesc = document.getElementById('review-description');
    if (reviewDesc) {
      reviewDesc.textContent = desc || 'None provided';
    }

    const conditions = [];
    document.querySelectorAll('#step-3 input[type="checkbox"]:checked').forEach(cb => {
      conditions.push(cb.value);
    });
    const reviewConditions = document.getElementById('review-conditions');
    if (reviewConditions) {
      reviewConditions.innerHTML = '';
      if (conditions.length > 0) {
        conditions.forEach(cond => {
          const span = document.createElement('span');
          span.className = 'review-tag';
          span.textContent = cond;
          reviewConditions.appendChild(span);
        });
      } else {
        reviewConditions.textContent = 'None reported';
      }
    }

    const meds = document.getElementById('current-medications')?.value.trim();
    const allergies = document.getElementById('known-allergies')?.value.trim();
    const reviewMeds = document.getElementById('review-meds');
    if (reviewMeds) reviewMeds.textContent = meds || 'None reported';
    const reviewAllergies = document.getElementById('review-allergies');
    if (reviewAllergies) reviewAllergies.textContent = allergies || 'No known drug allergies';
  }

  // Next / Submit Button
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (!validateCurrentStep()) return;

      if (currentStep < steps.length - 1) {
        showStep(currentStep + 1);
      } else {
        submitIntake();
      }
    });
  }

  // Back Button
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      if (currentStep > 0) {
        showStep(currentStep - 1);
      }
    });
  }

  // Collect Intake Data Payload
  function getIntakeData() {
    const symptoms = [];
    document.querySelectorAll('#step-1 input[type="checkbox"]:checked').forEach(cb => {
      symptoms.push(cb.value);
    });
    const otherSymptom = document.getElementById('other-symptom')?.value.trim();
    if (otherSymptom) symptoms.push(otherSymptom);

    const duration = document.querySelector('input[name="duration"]:checked')?.value || '';
    const description = document.getElementById('symptom-description')?.value.trim() || '';

    const conditions = [];
    document.querySelectorAll('#step-3 input[type="checkbox"]:checked').forEach(cb => {
      conditions.push(cb.value);
    });

    const medications = document.getElementById('current-medications')?.value.trim() || '';
    const allergies = document.getElementById('known-allergies')?.value.trim() || '';
    const notes = document.getElementById('additional-notes')?.value.trim() || '';

    return {
      symptoms,
      duration,
      severity: severityValue,
      description,
      medical_history: conditions,
      medications,
      allergies,
      additional_notes: notes,
    };
  }

  // Submit Intake Data & Process with Gemma 4 (Phase 3)
  async function submitIntake() {
    hideAlert();
    const payload = getIntakeData();

    // Show loading state
    steps.forEach(s => s && s.classList.remove('active'));
    wizardFooter.style.display = 'none';
    loadingOverlay.classList.add('active');

    try {
      // Step 1: Validate payload
      const valResponse = await fetch('/api/validate/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify(payload),
      });

      const valResult = await valResponse.json();
      if (!valResponse.ok || valResult.status !== 'validated') {
        throw new Error(valResult.error || 'Intake validation failed. Please review your entries.');
      }

      // Step 2: Process with Gemma 4 backend
      const aiResponse = await fetch('/api/process/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify(valResult.intake),
      });

      const aiResult = await aiResponse.json();
      loadingOverlay.classList.remove('active');

      if (aiResult.status === 'success' && aiResult.data) {
        // Display AI Structured Output
        renderAIResults(aiResult.data);
      } else if (aiResult.status === 'blocked') {
        // Display Blocker Notification (No API Key)
        renderAIBlocker(valResult.intake, aiResult.error);
      } else {
        throw new Error(aiResult.error || 'Failed to process intake with Gemma 4.');
      }
    } catch (err) {
      loadingOverlay.classList.remove('active');
      wizardFooter.style.display = 'flex';
      showStep(steps.length - 1);
      showAlert(err.message || 'An error occurred during intake processing. Please try again.');
    }
  }

  // Render Gemma 4 Structured Results
  function renderAIResults(data) {
    if (!aiResultsStep) return;

    // Chief Complaint
    const cc = document.getElementById('ai-chief-complaint');
    if (cc) cc.textContent = data.chief_complaint || 'Patient reported concern';

    // Symptoms
    const symContainer = document.getElementById('ai-structured-symptoms');
    if (symContainer) {
      symContainer.innerHTML = '';
      const symptoms = data.structured_symptoms || [];
      if (symptoms.length > 0) {
        symptoms.forEach(s => {
          const item = document.createElement('div');
          item.className = 'symptom-structured-item';
          item.innerHTML = `
            <div class="symptom-main-info">
              <span class="symptom-name">${escapeHTML(s.symptom || 'Symptom')}</span>
              <span class="symptom-meta">&bull; ${escapeHTML(s.reported_duration || 'Duration not specified')} &bull; Severity: ${escapeHTML(String(s.severity_score || 'Not rated'))}</span>
            </div>
            ${s.details ? `<div style="font-size: 13px; color: var(--secondary); width: 100%; margin-top: 4px;">${escapeHTML(s.details)}</div>` : ''}
          `;
          symContainer.appendChild(item);
        });
      } else {
        symContainer.textContent = 'No structured symptoms extracted.';
      }
    }

    // Timeline
    const timeline = document.getElementById('ai-timeline');
    if (timeline) timeline.textContent = data.timeline || 'Timeline not specified';

    // Medical History
    const conditionsEl = document.getElementById('ai-conditions');
    if (conditionsEl) {
      conditionsEl.innerHTML = '';
      const conds = data.medical_history?.chronic_conditions || [];
      if (conds.length > 0) {
        conds.forEach(c => {
          const span = document.createElement('span');
          span.className = 'review-tag';
          span.textContent = c;
          conditionsEl.appendChild(span);
        });
      } else {
        conditionsEl.textContent = 'None reported';
      }
    }

    // Medications & Allergies
    const medsEl = document.getElementById('ai-medications');
    if (medsEl) {
      const meds = data.medical_history?.current_medications;
      medsEl.textContent = Array.isArray(meds) ? (meds.join(', ') || 'None reported') : (meds || 'None reported');
    }

    const allergiesEl = document.getElementById('ai-allergies');
    if (allergiesEl) {
      const allergies = data.medical_history?.known_allergies;
      allergiesEl.textContent = Array.isArray(allergies) ? (allergies.join(', ') || 'No known drug allergies') : (allergies || 'No known drug allergies');
    }

    // Follow-up Questions (Only displayed when Gemma 4 identified missing info)
    const followupContainer = document.getElementById('ai-followup-container');
    const followupList = document.getElementById('ai-followup-list');
    const questions = data.follow_up_questions || [];

    if (followupContainer && followupList) {
      if (questions.length > 0) {
        followupList.innerHTML = '';
        questions.forEach((q, idx) => {
          const li = document.createElement('li');
          li.className = 'followup-item';
          li.innerHTML = `<span class="followup-num">Q${idx + 1}</span> <span>${escapeHTML(q)}</span>`;
          followupList.appendChild(li);
        });
        followupContainer.style.display = 'block';
      } else {
        followupContainer.style.display = 'none';
      }
    }

    // Safety disclaimer
    const safetyEl = document.getElementById('ai-safety-notice');
    if (safetyEl && data.clinical_safety_notice) {
      safetyEl.textContent = data.clinical_safety_notice;
    }

    aiResultsStep.classList.add('active');
    aiResultsStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Render AI Blocker Screen (When GEMINI_API_KEY is missing)
  function renderAIBlocker(intake, errorMsg) {
    if (!aiBlockerStep) return;

    const symContainer = document.getElementById('blocker-symptoms');
    if (symContainer) {
      symContainer.innerHTML = '';
      (intake.symptoms || []).forEach(s => {
        const span = document.createElement('span');
        span.className = 'review-tag';
        span.textContent = s;
        symContainer.appendChild(span);
      });
    }

    const durSev = document.getElementById('blocker-duration-severity');
    if (durSev) {
      durSev.textContent = `${(intake.duration || '').replace('_', ' ')} • Severity: ${intake.severity}/10`;
    }

    const desc = document.getElementById('blocker-description');
    if (desc) desc.textContent = intake.description || 'None provided';

    aiBlockerStep.classList.add('active');
    aiBlockerStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function escapeHTML(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Edit / Return to Intake buttons
  if (aiEditBtn) {
    aiEditBtn.addEventListener('click', () => {
      aiResultsStep.classList.remove('active');
      showStep(0);
    });
  }

  if (blockerEditBtn) {
    blockerEditBtn.addEventListener('click', () => {
      aiBlockerStep.classList.remove('active');
      showStep(0);
    });
  }
});
