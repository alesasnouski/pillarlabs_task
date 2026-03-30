document.addEventListener('alpine:init', () => {
    Alpine.data('annotationForm', () => ({
        loading: false,
        submitting: false,
        plan: '',

        screenshotUrl: null,
        screenshotError: null,
        screenshotLoading: false,
        debounceTimer: null,

        onUrlChange() {
            clearTimeout(this.debounceTimer);
            this.screenshotError = null;
            this.debounceTimer = setTimeout(() => this.fetchScreenshot(), 2000);
        },

        isValidUrl(url) {
            try {
                const parsed = new URL(url);
                return parsed.protocol === 'http:' || parsed.protocol === 'https:';
            } catch {
                return false;
            }
        },

        async fetchScreenshot() {
            const url = this.$refs.url.value.trim();
            if (!url) return;

            if (!this.isValidUrl(url)) {
                this.screenshotError = 'Invalid URL. Must start with http:// or https://';
                return;
            }

            this.screenshotLoading = true;
            try {
                const body = new FormData();
                body.append('url', url);
                body.append('csrf_token', this.$refs.csrfToken.value);

                const response = await fetch('/annotations/screenshot', {
                    method: 'POST',
                    body,
                });

                const data = await response.json();
                if (data.error) {
                    this.screenshotError = data.error;
                } else {
                    this.screenshotUrl = data.screenshot_url;
                }
            } catch (e) {
                this.screenshotError = 'Failed to capture screenshot.';
            } finally {
                this.screenshotLoading = false;
            }
        },

        get canSubmit() {
            const url = this.$refs.url ? this.$refs.url.value.trim() : '';
            return !url || this.screenshotUrl !== null;
        },

        async generate() {
            const url = this.$refs.url.value.trim();
            const prompt = this.$refs.prompt.value.trim();

            if (!url || !prompt) {
                alert('Please fill in Website and Prompt first.');
                return;
            }

            this.loading = true;
            try {
                const body = new FormData();
                body.append('url', url);
                body.append('prompt', prompt);
                body.append('csrf_token', this.$refs.csrfToken.value);

                const response = await fetch('/annotations/generate-plan', {
                    method: 'POST',
                    body,
                });

                if (!response.ok) throw new Error('Server error');

                const data = await response.json();
                if (data.plan) {
                    this.plan = data.plan;
                } else {
                    alert(data.error || 'Failed to generate plan.');
                }
            } catch (e) {
                alert(e.message);
            } finally {
                this.loading = false;
            }
        },
    }));
});
