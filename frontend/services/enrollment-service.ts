import { apiClient } from '@/services/api-client';

export interface UploadUrlResponse {
  upload_url: string;
  bucket: string;
  key: string;
  job_id: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED';
  error_message: string | null;
}

export interface ProcessJobResponse {
  job_id: string;
}

/**
 * Service for handling face enrollment operations.
 */
export const enrollmentService = {
  /**
   * Request a pre-signed URL for uploading an enrollment photo.
   * This also creates a PENDING job in the backend.
   */
  async getUploadUrl(): Promise<UploadUrlResponse> {
    return apiClient.post<UploadUrlResponse>('/enrollments/upload-url');
  },

  /**
   * Upload a photo to S3 using the pre-signed URL.
   * @param uploadUrl - The pre-signed S3 URL
   * @param imageUri - Local URI of the image to upload
   */
  async uploadPhotoToS3(uploadUrl: string, imageUri: string): Promise<void> {
    // Read the image as a blob
    const response = await fetch(imageUri);
    const blob = await response.blob();

    // Upload directly to S3
    const uploadResponse = await fetch(uploadUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': 'image/jpeg',
      },
      body: blob,
    });

    if (!uploadResponse.ok) {
      throw new Error(`S3 upload failed with status ${uploadResponse.status}`);
    }
  },

  /**
   * Trigger processing of an enrollment job after the photo has been uploaded.
   * @param jobId - The job ID returned from getUploadUrl
   */
  async processJob(jobId: string): Promise<ProcessJobResponse> {
    return apiClient.post<ProcessJobResponse>(`/enrollments/${jobId}/process`);
  },

  /**
   * Get the current status of an enrollment job.
   * @param jobId - The job ID to check
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    return apiClient.get<JobStatusResponse>(`/enrollments/${jobId}/status`);
  },

  /**
   * Poll for job completion with exponential backoff.
   * @param jobId - The job ID to poll
   * @param options - Polling options
   * @returns Final job status when completed or failed
   */
  async pollUntilComplete(
    jobId: string,
    options: {
      maxAttempts?: number;
      initialDelayMs?: number;
      maxDelayMs?: number;
      onStatusChange?: (status: JobStatusResponse) => void;
    } = {}
  ): Promise<JobStatusResponse> {
    const {
      maxAttempts = 30,
      initialDelayMs = 1000,
      maxDelayMs = 5000,
      onStatusChange,
    } = options;

    let attempts = 0;
    let delay = initialDelayMs;

    while (attempts < maxAttempts) {
      const status = await this.getJobStatus(jobId);
      onStatusChange?.(status);

      if (status.status === 'SUCCEEDED' || status.status === 'FAILED') {
        return status;
      }

      // Wait before next poll
      await new Promise((resolve) => setTimeout(resolve, delay));

      // Exponential backoff with max cap
      delay = Math.min(delay * 1.5, maxDelayMs);
      attempts++;
    }

    throw new Error('Job polling timed out');
  },

  /**
   * Complete enrollment flow: get URL, upload photo, process, and poll for completion.
   * @param imageUri - Local URI of the image to upload
   * @param onProgress - Optional callback for progress updates
   */
  async enrollFace(
    imageUri: string,
    onProgress?: (step: string, status?: JobStatusResponse) => void
  ): Promise<JobStatusResponse> {
    // Step 1: Get upload URL and job ID
    onProgress?.('Getting upload URL...');
    const { upload_url, job_id } = await this.getUploadUrl();

    // Step 2: Upload photo to S3
    onProgress?.('Uploading photo...');
    await this.uploadPhotoToS3(upload_url, imageUri);

    // Step 3: Trigger processing
    onProgress?.('Processing...');
    await this.processJob(job_id);

    // Step 4: Poll for completion
    const result = await this.pollUntilComplete(job_id, {
      onStatusChange: (status) => {
        onProgress?.(`Status: ${status.status}`, status);
      },
    });

    return result;
  },
};
