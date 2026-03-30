document.addEventListener('alpine:init', () => {
    Alpine.data('sessionForm', () => ({
        actionType: 'click',
        clickX: null,
        clickY: null,
        inputText: '',
        markerLeft: 0,
        markerTop: 0,
        description: '',
        finalResult: '',
        submitting: false,
        errorMsg: '',
        currentScreenshotUrl: null,

        get canSubmit() {
            if (!this.description.trim()) return false;
            if (this.actionType === 'click' && this.clickX === null) return false;
            if (this.actionType === 'type' && !this.inputText.trim()) return false;
            return true;
        },

        onScreenshotClick(event, img) {
            if (this.actionType !== 'click') return;

            const rect = img.getBoundingClientRect();
            const scaleX = img.naturalWidth / rect.width;
            const scaleY = img.naturalHeight / rect.height;

            this.clickX = Math.round((event.clientX - rect.left) * scaleX);
            this.clickY = Math.round((event.clientY - rect.top) * scaleY);

            // marker position on displayed image
            this.markerLeft = event.clientX - rect.left;
            this.markerTop = event.clientY - rect.top;
        },

        async submitAction(annotationId) {
            this.submitting = true;
            this.errorMsg = '';

            try {
                const body = new FormData();
                body.append('action_type', this.actionType);
                body.append('description', this.description);
                body.append('final_result', this.finalResult);
                body.append('csrf_token', this.$refs.csrfToken.value);

                if (this.actionType === 'click' && this.clickX !== null) {
                    body.append('click_axis_x', this.clickX);
                    body.append('click_axis_y', this.clickY);
                }

                if (this.actionType === 'type') {
                    body.append('input_text', this.inputText);
                }

                const response = await fetch(`/annotations/${annotationId}/action`, {
                    method: 'POST',
                    body,
                });

                const data = await response.json();

                if (data.error) {
                    this.errorMsg = data.error;
                    return;
                }

                this.currentScreenshotUrl = data.screenshot_url;
                this.clickX = null;
                this.clickY = null;
                this.inputText = '';
                this.description = '';
                this.finalResult = '';

                if (this.actionType === 'stop') {
                    window.location.href = `/annotations/${annotationId}`;
                }
            } catch (e) {
                this.errorMsg = 'Request failed: ' + e.message;
            } finally {
                this.submitting = false;
            }
        },
    }));
});
