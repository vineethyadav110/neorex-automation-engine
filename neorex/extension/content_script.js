/**
 * Neo.Rex Content Script
 * Injects Human-in-the-Loop (HITL) Review Layer and Workday Multi-Step Autofill Assistant.
 */

(function () {
  console.log("[Neo.Rex] Content script initialized on:", window.location.href);

  // 1. Detect ATS Platform
  function detectPlatform() {
    const host = window.location.hostname;
    const url = window.location.href;
    if (host.includes("myworkdayjobs.com") || host.includes("myworkday.com") || document.querySelector("[data-automation-id]")) {
      return "workday";
    }
    if (host.includes("greenhouse.io") || url.includes("gh_jid")) return "greenhouse";
    if (host.includes("lever.co")) return "lever";
    if (host.includes("ashbyhq.com")) return "ashby";
    if (host.includes("smartrecruiters.com")) return "smartrecruiters";
    return "generic";
  }

  function formatSlug(slug) {
    if (!slug) return "";
    return slug
      .replace(/[-_]+/g, " ")
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .replace(/\b\w/g, (c) => c.toUpperCase())
      .trim();
  }

  function cleanCompanyName(name) {
    if (!name) return "";
    return name
      .replace(/^(?:at|@|\bfor\b)\s+/i, "")
      .replace(/\s*(?:[-–|]\s*)?(?:Careers|Jobs|Hiring|Work with us|Job Application).*$/i, "")
      .trim();
  }

  // 2. Targeted Job Description and Metadata Extraction
  function extractJobDetails() {
    let title = "";
    let company = "";
    const platform = detectPlatform();
    const pathname = window.location.pathname;

    // TIER 1: JSON-LD Structured Data
    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of jsonLdScripts) {
      try {
        const data = JSON.parse(script.textContent);
        const item = Array.isArray(data) ? data.find(x => x["@type"] === "JobPosting") : (data["@type"] === "JobPosting" ? data : null);
        if (item) {
          if (item.title && !title) title = item.title.trim();
          if (item.hiringOrganization) {
            if (typeof item.hiringOrganization === "string") company = item.hiringOrganization.trim();
            else if (item.hiringOrganization.name) company = item.hiringOrganization.name.trim();
          }
        }
      } catch (e) {}
    }

    // TIER 2: OpenGraph & Meta Tags
    if (!company) {
      const ogSiteName = document.querySelector('meta[property="og:site_name"]');
      if (ogSiteName && ogSiteName.content) company = ogSiteName.content.trim();
    }
    if (!company) {
      const metaComp = document.querySelector('meta[name="company"], meta[property="business:contact_data:company_name"]');
      if (metaComp && metaComp.content) company = metaComp.content.trim();
    }

    // TIER 3: DOM Selectors & Platform Specific Containers
    if (!title) {
      const h1 = document.querySelector("h1, .app-title, .posting-headline h2, [data-testid='job-title'], [data-automation-id='jobPostingHeader']");
      if (h1) title = h1.innerText.trim();
    }

    if (!company) {
      const ghComp = document.querySelector("#header .company-name, .company-name, [data-testid='company-name']");
      if (ghComp) company = cleanCompanyName(ghComp.innerText);

      const leverOrg = document.querySelector(".posting-headline .main-header-logo + h2, .main-header-text");
      if (!company && leverOrg) company = cleanCompanyName(leverOrg.innerText);

      const ashbyOrg = document.querySelector("header h2, nav a[href*='ashbyhq']");
      if (!company && ashbyOrg) company = cleanCompanyName(ashbyOrg.innerText);

      const wdOrg = document.querySelector("[data-automation-id='companyLogo'], .css-1q8865, [data-automation-id='headerTitle']");
      if (!company && wdOrg) company = cleanCompanyName(wdOrg.innerText || wdOrg.getAttribute("alt") || "");
    }

    // TIER 4: ATS URL Path Token
    if (!company && platform !== "generic") {
      const segments = pathname.split("/").filter(Boolean);
      if (segments.length > 0 && segments[0] !== "jobs" && segments[0] !== "apply" && segments[0] !== "en-US") {
        company = formatSlug(segments[0]);
      } else if (segments.length > 1 && (segments[0] === "job-boards" || segments[0] === "jobs" || segments[0] === "en-US")) {
        company = formatSlug(segments[1]);
      }
    }

    // TIER 5: Document Title Fallback
    if (!company && document.title) {
      const docTitle = document.title;
      const matchAt = docTitle.match(/(?:at|@)\s+([^|\n–-]+)/i);
      if (matchAt && matchAt[1]) {
        company = cleanCompanyName(matchAt[1]);
      } else {
        const parts = docTitle.split(/[-–|]/);
        if (parts.length > 1) {
          company = cleanCompanyName(parts[parts.length - 1].trim());
        }
      }
    }

    company = cleanCompanyName(company) || "Target Company";
    title = title || document.title || "Target Role";

    // TARGETED JOB DESCRIPTION EXTRACTION
    const jdSelectors = [
      "#content .job-description", "#content", "#app-body", ".job-description", "#job_description", ".posting-content",
      ".posting-description", ".content-wrapper", ".posting-page",
      "[data-testid='job-posting-description']", ".ashby-job-posting-description",
      "[data-automation-id='jobPostingDescription']",
      "[data-qa='job-description']", ".job-sections",
      "article", "main", "[class*='description' i]", "[id*='description' i]"
    ];

    let jdContainer = null;
    for (const sel of jdSelectors) {
      const el = document.querySelector(sel);
      if (el && el.innerText && el.innerText.trim().length > 120) {
        jdContainer = el;
        break;
      }
    }

    if (!jdContainer) {
      jdContainer = document.body;
    }

    const jdClone = jdContainer.cloneNode(true);
    const noiseElements = jdClone.querySelectorAll(
      "script, style, nav, footer, header, noscript, " +
      "form, #application_form, #application-form, [data-testid='application-form'], " +
      "#demographic_questions, #eeo, .eeo-section, .compliance, [data-qa='job-application'], " +
      "#neorex-review-host, #neorex-floating-btn, #cf-toast, .cookie-banner, .privacy-policy"
    );
    noiseElements.forEach((el) => el.remove());

    let rawText = jdClone.innerText.trim();
    if (rawText.length > 25000) rawText = rawText.substring(0, 25000);

    return {
      title: title,
      company: company,
      url: window.location.href,
      raw_jd_text: rawText
    };
  }

  // 3. Floating In-Page Toast
  function showToast(message, isSuccess = true) {
    let toast = document.getElementById("cf-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "cf-toast";
      document.body.appendChild(toast);
    }

    toast.style.cssText = `
      position: fixed;
      top: 24px;
      right: 24px;
      z-index: 10000001;
      background: ${isSuccess ? '#065f46' : '#1e293b'};
      color: #ffffff;
      padding: 12px 20px;
      border-radius: 8px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.3);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 13.5px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
      transition: opacity 0.3s ease;
      border: 1px solid ${isSuccess ? '#10b981' : '#3b82f6'};
    `;
    toast.innerHTML = `<span>${isSuccess ? '📎' : '⏳'}</span> <span>${message}</span>`;

    if (isSuccess) {
      setTimeout(() => {
        if (toast) toast.style.opacity = "0";
        setTimeout(() => toast && toast.remove(), 400);
      }, 5000);
    }
  }

  // 4. Automated Cover Letter File Attachment (DataTransfer API)
  async function autoAttachCoverLetterFile(applicationId) {
    showToast("Generating and attaching tailored cover letter document in 3 seconds...", false);

    await new Promise((r) => setTimeout(r, 2500));

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/strategy/cover_letter_file/${applicationId}`);
      if (!res.ok) throw new Error("Could not retrieve cover letter file from server.");

      let filename = "Tailored_Cover_Letter.docx";
      const disposition = res.headers.get("Content-Disposition");
      if (disposition && disposition.includes("filename=")) {
        const matches = disposition.match(/filename=["']?([^"']+)["']?/);
        if (matches && matches[1]) filename = matches[1];
      }

      const blob = await res.blob();
      const file = new File([blob], filename, {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        lastModified: Date.now()
      });

      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);

      const fileInputs = Array.from(document.querySelectorAll("input[type='file']"));
      let targetInput = null;

      for (const input of fileInputs) {
        const name = (input.getAttribute("name") || "").toLowerCase();
        const id = (input.getAttribute("id") || "").toLowerCase();
        const aria = (input.getAttribute("aria-label") || "").toLowerCase();
        const parentText = (input.closest("fieldset, div, label")?.innerText || "").toLowerCase();

        if (name.includes("cover") || id.includes("cover") || aria.includes("cover") || parentText.includes("cover letter")) {
          targetInput = input;
          break;
        }
      }

      if (!targetInput && fileInputs.length > 1) {
        targetInput = fileInputs[1];
      }

      if (targetInput) {
        targetInput.files = dataTransfer.files;
        targetInput.dispatchEvent(new Event("input", { bubbles: true }));
        targetInput.dispatchEvent(new Event("change", { bubbles: true }));

        const dropzone = targetInput.closest(".dropzone, .drop-area, [data-source='attach'], .attach-or-paste");
        if (dropzone) {
          dropzone.dispatchEvent(new DragEvent("drop", { dataTransfer: dataTransfer, bubbles: true }));
        }

        console.log(`[Neo.Rex] Successfully auto-attached cover letter file '${filename}'`);
        showToast(`Auto-Attached Cover Letter: ${filename}`, true);
        return true;
      }
    } catch (err) {
      console.warn("[Neo.Rex] Cover letter attachment notice:", err.message);
    }
    return false;
  }

  // 5. Workday Post-Login Step Autofill Assistant
  async function autofillWorkdayActiveStep() {
    showToast("Scanning Workday wizard for empty fields...", false);

    try {
      const profileRes = await fetch("http://127.0.0.1:8000/api/profile");
      if (!profileRes.ok) throw new Error("Could not load candidate profile.");
      const profile = await profileRes.json();

      function setWorkdayVal(el, val) {
        if (!el || !val) return;
        el.focus();
        const proto = el instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        const desc = Object.getOwnPropertyDescriptor(proto, 'value');
        if (desc && desc.set) {
          desc.set.call(el, val);
        } else {
          el.value = val;
        }
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
        el.blur();
        el.style.border = "2px solid #10b981";
        el.style.backgroundColor = "#f0fdf4";
      }

      let count = 0;

      // 1. Text Inputs on Current Step
      const fieldMap = [
        { sel: "input[data-automation-id*='firstName'], input[data-automation-id*='legalNameSection_firstName']", val: profile.first_name },
        { sel: "input[data-automation-id*='lastName'], input[data-automation-id*='legalNameSection_lastName']", val: profile.last_name },
        { sel: "input[data-automation-id*='phone'], input[data-automation-id*='phoneNumber']", val: profile.phone },
        { sel: "input[data-automation-id*='city'], input[data-automation-id*='addressSection_city']", val: profile.city },
        { sel: "input[data-automation-id*='postalCode'], input[data-automation-id*='addressSection_postalCode']", val: profile.postal_code || "75001" },
        { sel: "input[data-automation-id*='linkedin' i], input[data-automation-id*='website']", val: profile.linkedin_url || "" }
      ];

      for (const item of fieldMap) {
        const el = document.querySelector(item.sel);
        if (el && (!el.value || el.value.trim() === "")) {
          setWorkdayVal(el, item.val);
          count++;
        }
      }

      // 2. Empty Textareas (Application Questions) via AI Screening Engine
      const emptyTextareas = Array.from(document.querySelectorAll("textarea[data-automation-id]")).filter(t => !t.value || t.value.trim() === "");
      const jobContext = extractJobDetails();

      for (const area of emptyTextareas) {
        const labelEl = area.closest("[data-automation-id*='formField']")?.querySelector("label");
        const qText = labelEl ? labelEl.innerText.trim() : "Screening Question";

        const res = await fetch("http://127.0.0.1:8000/api/screening/answer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question_text: qText,
            field_type: "textarea",
            company: jobContext.company,
            role_title: jobContext.title
          })
        });

        if (res.ok) {
          const ansData = await res.json();
          setWorkdayVal(area, ansData.answer);
          count++;
        }
      }

      showToast(`Workday Step Filled: ${count} boxes populated!`, true);
    } catch (err) {
      alert("Workday Assistant Error: " + err.message);
    }
  }

  // 6. Floating Action Button Injection
  function injectFloatingTrigger() {
    if (document.getElementById("neorex-floating-btn")) return;

    const platform = detectPlatform();
    const isWorkday = platform === "workday";

    const btn = document.createElement("div");
    btn.id = "neorex-floating-btn";
    btn.innerHTML = `
      <div style="
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 999999;
        background: #0f172a;
        color: #f8fafc;
        border: 1px solid ${isWorkday ? '#10b981' : '#3b82f6'};
        border-radius: 9999px;
        padding: 12px 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 10px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        font-weight: 600;
        transition: transform 0.15s ease;
      ">
        <span style="font-size: 18px;">${isWorkday ? '⚡' : '🎯'}</span>
        <span>${isWorkday ? '⚡ Neo.Rex: Fill Empty Boxes on This Step' : '🎯 Neo.Rex: Evaluate & Apply'}</span>
      </div>
    `;

    btn.addEventListener("click", () => {
      if (isWorkday) {
        autofillWorkdayActiveStep();
      } else {
        openReviewDrawer();
      }
    });

    document.body.appendChild(btn);
  }

  // 7. Standard No-Sign-In Review Drawer (Greenhouse, Lever, Ashby, etc.)
  async function openReviewDrawer() {
    let hostContainer = document.getElementById("neorex-review-host");
    if (!hostContainer) {
      hostContainer = document.createElement("div");
      hostContainer.id = "neorex-review-host";
      document.body.appendChild(hostContainer);
    }

    const shadow = hostContainer.attachShadow({ mode: "open" });
    shadow.innerHTML = `
      <style>
        .overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(15, 23, 42, 0.65);
          backdrop-filter: blur(4px);
          z-index: 1000000;
          display: flex;
          justify-content: flex-end;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          color: #0f172a;
        }
        .drawer {
          width: 560px;
          height: 100%;
          background: #ffffff;
          box-shadow: -10px 0 35px rgba(0,0,0,0.25);
          display: flex;
          flex-direction: column;
          overflow-y: auto;
          animation: slideIn 0.25s ease-out;
        }
        @keyframes slideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        .header {
          padding: 20px 24px;
          border-bottom: 1px solid #e2e8f0;
          background: #f8fafc;
          position: sticky;
          top: 0;
          z-index: 10;
        }
        .content {
          padding: 24px;
          flex: 1;
        }
        .score-box {
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 20px;
        }
        .score-val {
          font-size: 28px;
          font-weight: 700;
          color: #1d4ed8;
        }
        .attach-badge {
          background: #ecfdf5;
          border: 1px solid #a7f3d0;
          border-radius: 6px;
          padding: 10px 14px;
          margin-bottom: 18px;
          font-size: 13px;
          color: #065f46;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .field-group {
          margin-bottom: 16px;
        }
        .field-label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
          color: #475569;
          margin-bottom: 6px;
        }
        .input-text {
          width: 100%;
          padding: 9px 12px;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          font-size: 14px;
          box-sizing: border-box;
        }
        .textarea {
          width: 100%;
          min-height: 130px;
          padding: 10px 12px;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          font-size: 13px;
          line-height: 1.5;
          font-family: inherit;
          box-sizing: border-box;
        }
        .btn-row {
          padding: 18px 24px;
          border-top: 1px solid #e2e8f0;
          background: #f8fafc;
          position: sticky;
          bottom: 0;
          display: flex;
          gap: 12px;
        }
        .btn {
          flex: 1;
          padding: 12px;
          border-radius: 6px;
          font-weight: 600;
          font-size: 14px;
          cursor: pointer;
          border: none;
          text-align: center;
        }
        .btn-primary { background: #2563eb; color: #fff; }
        .btn-secondary { background: #e2e8f0; color: #334155; }
        .chip {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          margin-right: 6px;
          margin-bottom: 6px;
        }
        .chip-green { background: #dcfce7; color: #166534; }
        .chip-red { background: #fee2e2; color: #991b1b; }
      </style>

      <div class="overlay" id="cf-overlay">
        <div class="drawer">
          <div class="header">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div>
                <h3 style="margin: 0; font-size: 18px; color: #0f172a;">Application Review & Strategy</h3>
                <p style="margin: 4px 0 0; font-size: 13px; color: #64748b;">Target: <strong id="cf-company-label">Extracting...</strong> • Portal: <span style="text-transform: uppercase; font-weight: 600; color: #2563eb;">${detectPlatform()}</span></p>
              </div>
              <button id="cf-close-btn" style="background: none; border: none; font-size: 22px; cursor: pointer; color: #64748b;">✕</button>
            </div>
          </div>

          <div class="content" id="cf-content">
            <div style="text-align: center; padding: 50px 0; color: #64748b;">
              <p>Analyzing job requirements & preparing tailored application assets...</p>
            </div>
          </div>

          <div class="btn-row" id="cf-actions" style="display: none;">
            <button class="btn btn-secondary" id="cf-autofill-btn">⚡ Autofill & Auto-Attach File</button>
            <button class="btn btn-primary" id="cf-approve-btn">Approve & Save Strategy ✓</button>
          </div>
        </div>
      </div>
    `;

    shadow.getElementById("cf-close-btn").addEventListener("click", () => {
      hostContainer.remove();
    });

    const jobDetails = extractJobDetails();
    shadow.getElementById("cf-company-label").textContent = `${jobDetails.company}`;

    try {
      const response = await fetch("http://127.0.0.1:8000/api/review/prepare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(jobDetails)
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const payload = await response.json();
      renderReviewContent(shadow, payload, hostContainer);
    } catch (err) {
      shadow.getElementById("cf-content").innerHTML = `
        <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 16px; color: #991b1b;">
          <strong>Backend Service Connection Error</strong>
          <p style="margin: 8px 0 0; font-size: 13px;">Ensure FastAPI backend is running on <code>http://127.0.0.1:8000</code>.</p>
        </div>
      `;
    }
  }

  function renderReviewContent(shadow, payload, hostContainer) {
    const contentEl = shadow.getElementById("cf-content");
    const actionsEl = shadow.getElementById("cf-actions");
    actionsEl.style.display = "flex";

    const evalData = payload.evaluation;

    let matchedChips = evalData.matched_skills.map(s => `<span class="chip chip-green">✓ ${s}</span>`).join("");
    let missingChips = evalData.missing_required_skills.map(s => `<span class="chip chip-red">✗ ${s}</span>`).join("");

    let fieldsHtml = payload.mapped_fields.map(f => `
      <div class="field-group">
        <label class="field-label">${f.label} ${f.required ? '<span style="color:red">*</span>' : ''}</label>
        <input type="${f.field_type === 'email' ? 'email' : 'text'}" class="input-text" data-field-id="${f.field_id}" value="${f.value || ''}">
      </div>
    `).join("");

    contentEl.innerHTML = `
      <div class="score-box">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-size: 12px; text-transform: uppercase; font-weight: 700; color: #64748b;">Job Alignment Score</div>
            <div class="score-val">${evalData.overall_score}%</div>
          </div>
          <span style="font-size: 13px; font-weight: 700; background: #dbeafe; color: #1e40af; padding: 4px 10px; border-radius: 9999px;">
            ${evalData.match_category}
          </span>
        </div>
        <div style="margin-top: 10px; font-size: 13px; color: #334155;">
          ${evalData.experience_fit_summary}
        </div>
      </div>

      <div class="attach-badge">
        <span>📎</span>
        <div>
          <strong>Auto-Attach Engine Armed:</strong> Tailored DOCX cover letter will be attached to portal form 3s after clicking Autofill.
        </div>
      </div>

      <div style="margin-bottom: 20px;">
        <div class="field-label">Matched Competencies (${evalData.matched_skills.length})</div>
        <div>${matchedChips || '<span style="font-size:12px;color:#94a3b8">None</span>'}</div>
      </div>

      ${missingChips ? `
        <div style="margin-bottom: 20px;">
          <div class="field-label">Missing Core Requirements</div>
          <div>${missingChips}</div>
        </div>
      ` : ''}

      <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">

      <h4 style="margin: 0 0 16px; font-size: 15px; color: #0f172a;">Application Form Data Verification</h4>
      ${fieldsHtml}

      <div class="field-group">
        <label class="field-label">Tailored Cover Letter (Target: ${payload.job.company})</label>
        <textarea class="textarea" id="cf-cover-letter">${payload.tailored_cover_letter || ''}</textarea>
      </div>
    `;

    shadow.getElementById("cf-autofill-btn").addEventListener("click", async () => {
      const inputs = shadow.querySelectorAll(".input-text");
      for (const input of inputs) {
        const fieldId = input.getAttribute("data-field-id");
        await fetch("http://127.0.0.1:8000/api/review/update_field", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            application_id: payload.application_id,
            field_id: fieldId,
            new_value: input.value
          })
        });
      }

      const clVal = shadow.getElementById("cf-cover-letter").value;
      await fetch("http://127.0.0.1:8000/api/review/update_field", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          application_id: payload.application_id,
          field_id: "cover_letter",
          new_value: clVal
        })
      });

      const scriptRes = await fetch(`http://127.0.0.1:8000/api/autofill_script/${payload.application_id}`);
      const scriptData = await scriptRes.json();

      const scriptEl = document.createElement("script");
      scriptEl.textContent = scriptData.script;
      document.body.appendChild(scriptEl);
      scriptEl.remove();

      autoAttachCoverLetterFile(payload.application_id);
    });

    shadow.getElementById("cf-approve-btn").addEventListener("click", async () => {
      try {
        await fetch("http://127.0.0.1:8000/api/review/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            application_id: payload.application_id,
            notes: "Approved via Option A review workflow."
          })
        });

        const stratRes = await fetch("http://127.0.0.1:8000/api/strategy/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            application_id: payload.application_id
          })
        });

        const stratData = await stratRes.json();
        autoAttachCoverLetterFile(payload.application_id);

        alert(`✅ Application Approved & Strategy Synced!\n\nTarget: ${payload.job.company} - ${payload.job.title}\nMatch: ${evalData.overall_score}%\nCover Letter: ${stratData.cover_letter_file}\nTracker Status: ${stratData.tracker_status}`);
        hostContainer.remove();
      } catch (err) {
        alert("Error approving application: " + err.message);
      }
    });
  }

  window.addEventListener("load", () => {
    setTimeout(injectFloatingTrigger, 800);
  });
})();
