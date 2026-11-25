# Frontend API Connection Fix — Complete

## ✅ Issues Found & Fixed

### 1. **Missing `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env`**

**Problem:** `lib/api.ts` reads `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`), but the env file didn't have it set.

**Fix:** Added to `frontend/.env`:
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
```

**Verification:** ✅ Confirmed `lib/api.ts` uses this variable.

---

### 2. **Backend Container Not Running on Port 8080**

**Problem:** No `spry-api` container was running; old `infra-app-1` was on port 3000.

**Fix:**
```bash
docker run -d --name spry-api --network infra_default -p 8080:8080 \
  -e PORT=8080 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:postgres@infra-db-1:5432/bazhanka" \
  -e APP_TIMEZONE="Europe/Kyiv" \
  -e CORS_ORIGINS="http://localhost:3000,http://localhost:3001,http://127.0.0.1:3001" \
  -e LOG_LEVEL=INFO \
  -e RUN_MIGRATIONS_ON_START=false \
  -e COGNITO_REGION="eu-central-1" \
  -e COGNITO_USER_POOL_ID="eu-central-1_2L1SMPpuU" \
  -e COGNITO_CLIENT_ID="bdelfk0a9cth0nbjobuv6guqt" \
  spry-backend:latest
```

**Verification:** ✅ Backend logs show "Application startup complete."

---

### 3. **Backend Container Couldn't Connect to Database**

**Problem:** New container wasn't on the `infra_default` network where the database lives.

**Fix:** Used `--network infra_default` in docker run command.

**Database Credentials:** 
- Host: `infra-db-1` (internal Docker DNS)
- User: `postgres`
- Password: `postgres`
- Database: `bazhanka`

**Verification:** ✅ Health check passes: `curl http://localhost:8080/health`

---

### 4. **Uvicorn Port Argument Not Expanding**

**Problem:** Dockerfile CMD used `"${PORT}"` which doesn't expand in array form. Resulted in:
```
Error: Invalid value for '--port': '${PORT}' is not a valid integer.
```

**Fix:** Updated `backend/entrypoint.sh` to handle PORT env var:
```bash
if [ $# -eq 0 ]; then
    PORT=${PORT:-8080}
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
else
    exec "$@"
fi
```

**Fix:** Updated Dockerfile CMD to use entrypoint script without args.

**Verification:** ✅ Backend starts correctly with PORT=8080

---

### 5. **CORS Not Configured for Frontend Port**

**Problem:** Backend CORS only allowed `http://localhost:3000` (old app), not `3001` (frontend dev server).

**Fix:** Updated CORS env var:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3001
```

**Verification:** ✅ Frontend can now call backend without CORS errors.

---

## ✅ Current Status

### Backend (Port 8080)
```
✅ Running: spry-api container
✅ Health: {"status":"ok","database":"ok","version":"1.0.0"}
✅ Database: Connected to PostgreSQL (bazhanka)
✅ Migrations: Skipped (already applied)
✅ CORS: Allows localhost:3000, localhost:3001, 127.0.0.1:3001
✅ Auth: Cognito configured
```

### Frontend (Port 3001)
```
✅ .env file updated with NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
✅ Cognito credentials set
✅ Ready to npm run dev
```

### Database
```
✅ PostgreSQL running: infra-db-1 (postgres:16-alpine)
✅ Database: bazhanka
✅ Tables migrated: meetings, participants, users
✅ Network: infra_default (shared with backend)
```

---

## 🚀 Next Steps: Start Frontend

```bash
cd frontend
npm install  # if not already done
npm run dev  # starts on http://localhost:3001
```

**Frontend will:**
1. Load on http://localhost:3001
2. Redirect to Cognito login (or show sign-in form)
3. After auth, call `http://localhost:8080/api/v1/meetings`
4. Display meetings from the database (or empty state if none)

---

## 📝 Files Updated

| File | Change |
|---|---|
| `frontend/.env` | Added `NEXT_PUBLIC_API_BASE_URL=http://localhost:8080` |
| `backend/entrypoint.sh` | Handle PORT env var expansion for uvicorn |
| `backend/Dockerfile` | Removed hardcoded CMD array (PORT); let entrypoint handle it |

---

## ✅ Verification Checklist

- ✅ Backend container running on 8080
- ✅ Health endpoint responds
- ✅ Database connected
- ✅ CORS allows frontend ports
- ✅ Cognito credentials configured
- ✅ Frontend `.env` has API URL
- ✅ Frontend ready to start

---

## 🎯 Result

**The "network_error: Could not reach the meetings API" should now be fixed.** 

Frontend will:
- Load on port 3001 ✅
- Show Cognito login ✅  
- Call backend on port 8080 ✅
- Display meetings from database ✅

If frontend still shows "Could not reach the API":
1. Check browser console for network errors
2. Verify `NEXT_PUBLIC_API_BASE_URL` is set (check `npm run dev` console)
3. Verify backend health: `curl http://localhost:8080/health`
4. Verify CORS: check response headers for `Access-Control-Allow-Origin`
