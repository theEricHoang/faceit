# FaceIT — AWS Async Recognition Design (School-Project / Low-Cost)

## 1) Conversation Goal (Summary)

Build a face-based attendance system with:

- **Supabase Auth** for users (student/instructor) and **Supabase Postgres as the main database**.
- **Student enrollment**: student uploads 1+ face photos → async job generates **InsightFace embeddings** → embeddings stored and associated to the student account.
- **Attendance capture**: instructor uploads class photo(s) → async job detects/embeds faces → matches to enrolled students → creates an attendance report.
- **Constraints**:
  - Very low throughput (≈ 2–3 uploads/day).
  - Not near-real-time.
  - Prefer storing **embeddings** and only **short-lived images**.
  - Worker should run **entirely on AWS**.
  - Keep spend as close to $0 as possible (accepting that AWS may not be literally $0).

---

## 2) High-Level Architecture

### What stays in Supabase

- **Identity**: Supabase Auth (JWTs verified by backend).
- **Main DB**: Supabase Postgres holds:
  - enrollments + embeddings
  - attendance sessions + results
  - job status

This avoids operating any DB on AWS and keeps AWS scope to “storage + queue + compute”.

### What runs on AWS

- **S3**: temporary storage for uploaded photos (raw enrollment images and class images) with lifecycle deletion.
- **SQS**: queues for async processing.
- **ECS Fargate (Task)**: an on-demand worker container that runs InsightFace inference on CPU (fine for low volume).
- **EventBridge Scheduler**: starts the worker task periodically (batch processing), so no always-on compute.
- **Secrets Manager**: stores Supabase service key + JWT secret (and any other secrets).
- **CloudWatch**: logs and alarms.

> Why ECS Fargate + scheduled tasks?
> - At your volume, the cheapest practical setup is “**run worker only sometimes**” and let jobs wait.
> - Fargate charges only while tasks run.
> - Avoids long-running EC2 or GPU instances.

---

## 3) Data Flow

### 3.1 Enrollment flow (student)

1. **Client → API**: request an upload URL
   - `POST /enrollment/photos/upload-url`
2. **API → S3**: returns a **pre-signed PUT URL** (and `s3_key`).
3. **Client → S3**: uploads the image.
4. **Client → API**: confirms upload / creates job
   - `POST /jobs` with `{type: "ENROLLMENT", s3_key}`
5. **API → DB (Supabase)**: inserts a `jobs` row (`PENDING`).
6. **API → SQS**: sends message `{job_id, user_id, s3_key, kind:"ENROLLMENT"}`.
7. **Scheduled ECS worker** wakes up, drains messages:
   - downloads image from S3
   - detects face(s)
   - generates embedding(s)
   - writes embeddings to Supabase Postgres
   - marks job `SUCCEEDED` or `FAILED`
8. **Client polls**: `GET /jobs/{job_id}` until done.

Enrollment acceptance rules (MVP):
- Fail if **no face** detected.
- Fail if **multiple faces** detected (or choose best face; pick one rule and document it).
- Store a `quality_score` so you can later reject low-quality embeddings.

### 3.2 Attendance flow (instructor)

1. **Client → API**: request an upload URL
   - `POST /classes/{class_id}/attendance/upload-url`
2. **Client → S3**: upload class image.
3. **Client → API**: create job
   - `POST /jobs` with `{type:"ATTENDANCE", class_id, s3_key}`
4. **API → DB**: create `attendance_session` + `jobs` row.
5. **API → SQS**: enqueue `{job_id, class_id, instructor_id, s3_key, kind:"ATTENDANCE"}`.
6. **Worker**:
   - detect faces, compute embedding per face
   - query Supabase for enrolled embeddings for that class roster (or for the whole school for MVP)
   - nearest-neighbor match with thresholds
   - persist attendance results
   - mark job done

Matching rules (MVP):
- Use **cosine similarity** on **L2-normalized** embeddings.
- Apply a similarity threshold; optionally also require a “margin” between top-1 and top-2.
- Record `UNKNOWN` faces without storing the raw face image.

---

## 4) Minimal AWS Setup (Low Cost)

### 4.1 S3

- One bucket, e.g. `faceit-uploads-<env>`
- Prefixes:
  - `enrollment-photos/` (short-lived)
  - `class-photos/` (short-lived)
- **Lifecycle rule**: delete objects after 1 day (or shorter).
- Bucket policy: block public access; allow only via signed URLs and ECS task role.

### 4.2 SQS

- `faceit-enrollment-queue`
- `faceit-attendance-queue`
- DLQ per queue:
  - `faceit-enrollment-dlq`
  - `faceit-attendance-dlq`

Recommended settings:
- Visibility timeout: worker max processing time + buffer
- Max receive count to DLQ: e.g. 3–5

### 4.3 ECS Fargate worker (scheduled)

- Build a Docker image with:
  - Python worker code
  - InsightFace dependencies (CPU)
  - `boto3` for AWS
  - Supabase Python client to write results
- Run as a **Fargate Task** (not a Service).
- Task behavior:
  - poll both queues for up to N minutes (e.g., 10–15)
  - process messages until empty
  - exit successfully

### 4.4 EventBridge Scheduler

- Runs every 15 minutes (or hourly) to start the ECS task.
- This removes the need for “always-on” consumers.

> With 2–3 uploads/day, hourly processing is typically acceptable.

### 4.5 Secrets

Store in **AWS Secrets Manager**:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_JWT_SECRET` (if your API is also hosted on AWS)

Worker requires only `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`.

### 4.6 IAM

- ECS task **execution role**: pull image, write logs.
- ECS task **task role**: minimal permissions:
  - `s3:GetObject` on bucket/prefixes
  - `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes`
  - `secretsmanager:GetSecretValue`

---

## 5) Supabase DB: Suggested Tables (Schema Sketch)

These models/schemas in the repo are currently scaffolds; this section is a proposed starting point.

### 5.1 `jobs`

- `id` (uuid, pk)
- `kind` (text: `ENROLLMENT` | `ATTENDANCE`)
- `status` (text: `PENDING` | `RUNNING` | `SUCCEEDED` | `FAILED`)
- `owner_user_id` (uuid) — student or instructor who initiated
- `class_id` (uuid, nullable)
- `s3_bucket` (text)
- `s3_key` (text)
- `error_code` (text, nullable)
- `error_message` (text, nullable)
- `created_at`, `updated_at`

### 5.2 `face_embeddings`

- `id` (uuid, pk)
- `user_id` (uuid, indexed)
- `model` (text, e.g. `insightface-buffalo_l`)
- `embedding` (vector(512) if pgvector enabled; otherwise float[])
- `quality_score` (float)
- `created_at`

### 5.3 `attendance_sessions`

- `id` (uuid, pk)
- `class_id` (uuid)
- `instructor_id` (uuid)
- `job_id` (uuid)
- `captured_at` (timestamp)
- `created_at`

### 5.4 `attendance_results`

- `id` (uuid, pk)
- `session_id` (uuid)
- `student_user_id` (uuid, nullable) — null means UNKNOWN
- `confidence` (float)
- `matched_embedding_id` (uuid, nullable)
- `face_index` (int) — index of face in detection list
- `created_at`

> Note: You can keep results minimal for privacy (no face crops).

### pgvector note

If you can enable `pgvector` in Supabase, it keeps everything simple:
- similarity search in SQL
- a single DB system

If not available, you can still store embeddings and do matching in the worker in Python.

---

## 6) API Endpoints (MVP)

- `POST /enrollment/photos/upload-url`
  - auth: student
  - returns: `{upload_url, bucket, key}`

- `POST /classes/{class_id}/attendance/upload-url`
  - auth: instructor
  - returns: `{upload_url, bucket, key}`

- `POST /jobs`
  - body: `{kind, bucket, key, class_id?}`
  - inserts `jobs` row + enqueues SQS message
  - returns: `{job_id}`

- `GET /jobs/{job_id}`
  - returns: `{status, error?, result_summary?}`

- `GET /classes/{class_id}/attendance/sessions/{session_id}`
  - returns: recognized roster + unknown count

---

## 7) Worker Implementation Notes

### Idempotency

SQS can deliver messages more than once.

Worker should be safe if it processes the same `job_id` twice:
- Use `jobs.status` transitions with checks:
  - if already `SUCCEEDED`, no-op
  - if `RUNNING` but stale, allow takeover
- Use unique constraints for embeddings if needed.

### Error handling

- Any exception should:
  - mark job `FAILED` with `error_code`
  - let SQS retry (until DLQ) OR delete message after storing failure (choose one policy)

Recommendation for MVP:
- **Delete message after marking FAILED** (prevents retry storms).
- Keep DLQ anyway for truly unhandled failures.

### Model versioning

Always store `model` (and optionally a `model_version`) so you can re-embed later.

---

## 8) Cost Controls (Do This Immediately)

- **AWS Budgets**: set a $1–$5 monthly budget and alerts.
- **Avoid NAT Gateway**: it’s a common “surprise bill”.
- **No GPU** for MVP: CPU inference is acceptable at your scale.
- **S3 lifecycle deletion**: aggressively delete raw images.
- **CloudWatch retention**: set 7–14 day retention.
- **Tag everything**: `project=faceit`, `env=dev` so you can audit costs.

Reality check: “$0 forever” on AWS is hard; but with S3 + SQS + a few short Fargate task runs/week, the bill can be kept very small.

---

## 9) MVP Milestones

1. **DB tables** in Supabase: `jobs`, `face_embeddings`, `attendance_sessions`, `attendance_results`.
2. **FastAPI endpoints**: pre-signed upload URLs + `POST /jobs` + `GET /jobs/{id}`.
3. **S3 bucket + lifecycle** and SQS queues + DLQs.
4. **Worker container** (ECS Fargate task) that:
   - processes enrollment jobs end-to-end
   - writes embeddings to Supabase
5. Extend worker to **attendance jobs** and produce attendance results.
6. Add minimal frontend screens:
   - enroll status
   - attendance session status + results

---

## 10) Growth Path (If This Becomes Real)

- Replace scheduled polling with event-driven start/stop:
  - Lambda trigger on SQS depth → start ECS task (with a distributed lock)
- Add GPU workers (ECS on EC2 GPU, Batch, or EKS) when throughput demands.
- Add better matching:
  - per-class candidate sets (only enrolled students in that class)
  - liveness checks / anti-spoofing (if required)
- Stronger privacy controls and audits.
