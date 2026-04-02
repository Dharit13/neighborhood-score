# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-03-30

### Added

- AI-powered neighbourhood report with 17 scoring dimensions (safety, affordability, transit access, flood risk, commute, walkability, hospital access, water supply, air quality, school access, noise, power reliability, future infrastructure, cleanliness, builder reputation, delivery coverage, business opportunity)
- Data-enriched claim verification pipeline that cross-references builder marketing claims against permit records, satellite imagery, and public data sources
- Property intelligence platform with builder profiles, project timelines, and slug-based routing (`/api/builders`, `/api/builder/{slug}`, `/api/search`)
- Builder trust score computation using a 7-factor weighted formula (delivery track record, RERA compliance, legal disputes, financial health, customer reviews, project quality, transparency)
- AI chat endpoint with neighbourhood summary context built from 12 LEFT JOINs across scoring tables
- 3D depth parallax effects on the landing page hero section for visual engagement
- Newspaper-style hero headline layout for the main landing page
- Login page with authentication flow
- Compare mode allowing side-by-side neighbourhood comparison via guided questionnaire
- Radar chart visualisation for multi-dimensional neighbourhood scoring
- Map sidebar with search autocomplete and interactive pin-based exploration
- Builder card expansion UI for detailed builder information
- Demo polish pass with improved branding, logo, and colour palette
- Comprehensive test suite for backend and frontend
- CI pipeline with GitHub Actions for linting, type checking, and tests
- `uv` for Python dependency management and reproducible installs
- `ty` for Python type checking
- Makefile with standard development commands (lint, test, format, run)
- Security hardening: input validation, rate limiting, and dependency audit

### Changed

- Upgraded project to open-source readiness with standardised tooling and contribution guidelines
- Improved UI polish across all frontend components (spacing, typography, colour consistency)

### Fixed

- All remaining ESLint errors and warnings reduced to zero across the frontend codebase
- All ruff linting violations resolved across the backend codebase
- All ty type errors resolved across the backend codebase
- All ESLint type and lint errors resolved in frontend TypeScript files
