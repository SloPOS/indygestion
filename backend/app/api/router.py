from fastapi import APIRouter

from app.api import activity, clips, dashboard, devices, ingest, jobs, projects, settings, upload

api_router = APIRouter()
api_router.include_router(projects.router)
api_router.include_router(clips.router)
api_router.include_router(upload.router)
api_router.include_router(ingest.router)
api_router.include_router(jobs.router)
api_router.include_router(devices.router)
api_router.include_router(settings.router)
api_router.include_router(activity.router)
api_router.include_router(dashboard.router)
