# CodeCraftHub API

CodeCraftHub is a beginner-friendly REST API for managing courses.

It is built with Python and Flask and stores course data in a local JSON file named `courses.json`. No database is required.

This project demonstrates the basic REST API operations known as CRUD:

- **Create** a course
- **Read** courses
- **Update** a course
- **Delete** a course

It also includes a statistics endpoint that counts courses by status.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Technologies Used](#technologies-used)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Course Data](#course-data)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [REST API Concepts](#rest-api-concepts)
- [Production Notes](#production-notes)

---

## Project Overview

CodeCraftHub provides an API for creating and managing courses.

Each course contains:

|
Field
|
Description
|
|

---

## |

|
|
`id`
|
Automatically generated numeric ID
|
|
`name`
|
Course name
|
|
`description`
|
Course description
|
|
`target_date`
|
Target completion date in
`YYYY-MM-DD`
format
|
|
`status`
|
Course progress status
|
|
`created_at`
|
Automatically generated creation timestamp
|

Course data is stored in:

```text
courses.json
```
