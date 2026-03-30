document.addEventListener('alpine:init', () => {
    Alpine.data('annotationForm', () => ({
        loading: false,
        plan: '',

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
