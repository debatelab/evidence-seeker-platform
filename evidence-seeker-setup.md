# Evidence Seeker Setup (Hugging Face Inference API)

This guide walks through configuring a brand-new Evidence Seeker instance so it uses Hugging Face’s Inference API for embeddings as well as the downstream preprocessor/confirmation stages. Everything is done through the platform UI; no manual YAML editing required.

---

## Prerequisites

- A running instance of the platform (backend + frontend).
- Evidence Seeker admin access for the organisation you are configuring.
- A Hugging Face Inference Provider key with access to the models you plan to use.
- Optional: a Hugging Face Hub token if you need to download an index from the Hub.

---

## 1. Create the Evidence Seeker

1. Sign in to the UI with an account that has platform admin rights.
2. Navigate to **Platform → Evidence Seekers**.
3. Click **New Evidence Seeker**, provide the basic details (name, description), and submit.
4. Add yourself (and any teammates) as **EVSE_ADMIN** so you can modify settings later.

---

## 2. Store the Hugging Face API Key

We will reuse this key for both embeddings and the rest of the pipeline.

1. In the Evidence Seeker list, open the seeker you just created.
2. Switch to the **API Keys** tab.
3. Click **Add API Key** and fill in:
   - **Provider:** `huggingface`
   - **Name:** e.g. `HF Inference`
   - **API Key:** paste the raw Hugging Face token (begins with `hf_`).
   - Optional: add a description and expiry.
4. Save. The key is encrypted and stored and will later be selectable from the settings page.

> TIP: if you also need a separate Hub token for downloading an index, repeat the steps above with a different name.

---

## 3. Configure Embedding Settings

1. Open the **Pipeline Settings** tab for your seeker.
2. Fill in the **Default model** with the embedding model you want:
   ```
   BAAI/bge-m3
   ```
3. Under **Embedding backend**, choose **Hugging Face Inference API**.
4. Provide the endpoint Hugging Face expects:
   ```
   https://router.huggingface.co/hf-inference/models/BAAI/bge-m3
   ```
5. Set **Billing organisation** if the usage should be charged to a Hugging Face org (value for `X-HF-Bill-To`). (e.g. DebateLabKIT)
6. Use the **Hugging Face API key** dropdown to pick the credential you just stored (leave it on **None** for now if you still need to add one in the API Keys section below).
7. Leave **Trust remote code** at the default unless the model requires it.
8. Save the settings.

Behind the scenes this seeds `embed_backend_type`, `embed_model_name`, `embed_base_url`, and the API key reference that the retriever will consume via `EVSE_HF_API_KEY_<settings_id>`.

---

## 4. Add Pipeline Overrides (LLM / Confirmation)

The rest of the pipeline still needs a model configuration. Convert your YAML to JSON (for example using <https://jsonformatter.org/yaml-to-json>) and paste it into **Pipeline overrides**. A minimal example that mirrors the documentation:

```json
{
  "timeout": 1200,
  "env_file": null,
  "used_model_key": "Llama-3.3-70B-Instruct",
  "models": {
    "Llama-3.3-70B-Instruct": {
      "name": "Llama-3.3-70B-Instruct",
      "description": "Llama-3.3-70B served by Together.ai over Hugging Face",
      "base_url": "https://router.huggingface.co/v1",
      "model": "meta-llama/Llama-3.3-70B-Instruct:together",
      "api_key_name": "EVSE_HF_API_KEY_PLACEHOLDER",
      "backend_type": "openai",
      "default_headers": {
        "X-HF-Bill-To": "your_hugging_face_organisation"
      },
      "max_tokens": 1024,
      "temperature": 0.2,
      "timeout": 260
    }
  }
}
```

**Important adjustments:**

- Replace the `api_key_name` value with the env var the platform sets. For keys saved through the UI it is `EVSE_HF_API_KEY_<settings_id>` (visible under **Metadata filters** preview or via the database). If you only have one key the ID is usually `1`, resulting in `EVSE_HF_API_KEY_1`.
- Remove `env_file` if you are not using on-disk `.env` files.
- Update `model`, `base_url`, or headers if you are targeting a different hosted LLM.

Re-save after pasting the JSON.

---

## 5. Metadata Filters & Index Storage

- The platform automatically injects `{"evidence_seeker_id": "<uuid>"}` so each seeker only sees its own documents. Add extra filters in the UI as JSON if needed (language, tags, etc.).
- If you plan to bootstrap from a Hugging Face Hub index, set `index_hub_path` / `index_persist_path` in the overrides as well (match the documentation snippet). Otherwise leave them blank to rely on PostgreSQL storage.

---

## 6. Validate the Configuration

1. Use **Test Configuration** on the settings page. This performs a lightweight metadata filter check via the configured Inference API.
2. Upload a small document in **Documents → Upload** to trigger an indexing job.
3. Watch **Progress → Index Jobs** for a successful run. The backend calls the HF endpoint instead of downloading local models.
4. Finally run a fact-check from the UI; the cached pipeline should reuse the same HF key and confirm everything is wired.

---

## Troubleshooting

- **“embed_base_url must be set”** – you selected the inference backend but left the URL empty; copy it from the Hugging Face model page.
- **“A Hugging Face API key is required …”** – pick a stored key in the settings, or create one first in the API Keys tab.
- **403 from Hugging Face** – the key lacks access to the chosen model; confirm billing and repository permissions in your Hugging Face account.
- **Config overrides not applied** – ensure your JSON uses double quotes and valid syntax. The UI rejects invalid JSON silently; use the test button to surface errors.

---

Once those steps are complete, your Evidence Seeker instance is fully hosted on Hugging Face’s Inference Provider: embeddings, preprocessing, and confirmation all run remotely, letting you avoid local model downloads entirely.
