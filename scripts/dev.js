#!/usr/bin/env node
"use strict"

const { spawn } = require("child_process")
const path = require("path")

const rootDir = path.resolve(__dirname, "..")

const tasks = [
    {
        label: "db",
        command: "docker-compose -f docker-compose.dev.yml up db",
        cwd: rootDir,
    },
    {
        label: "backend",
        command: ". .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000",
        cwd: path.join(rootDir, "backend"),
    },
    {
        label: "frontend",
        command: "npm run dev",
        cwd: path.join(rootDir, "frontend"),
    },
]

const processes = []
let stopping = false

function stopAll(signal = "SIGTERM") {
    if (stopping) {
        return
    }
    stopping = true
    console.log(`\nReceived ${signal}, stopping dev services...`)

    for (const { label, child } of processes) {
        if (child.exitCode != null || child.signalCode != null) {
            continue
        }
        try {
            process.kill(-child.pid, signal)
        }
        catch (error) {
            if (error.code !== "ESRCH") {
                console.error(`[dev] Failed to stop ${label}: ${error.message}`)
            }
        }
    }
}

function handleExit(result) {
    if (!stopping && result.signal == null && result.code !== 0) {
        console.error(`[dev] ${result.label} exited with code ${result.code}, shutting down the others.`)
        stopAll("SIGTERM")
    }
}

async function main() {
    const exitPromises = tasks.map((task) => {
        return new Promise((resolve, reject) => {
            console.log(`[dev] starting ${task.label}...`)
            const child = spawn(task.command, {
                cwd: task.cwd,
                shell: true,
                stdio: "inherit",
                detached: true,
            })

            processes.push({ label: task.label, child })

            child.on("error", (error) => {
                console.error(`[dev] ${task.label} failed to start: ${error.message}`)
                stopAll("SIGTERM")
                reject(error)
            })

            child.on("exit", (code, signal) => {
                const result = { label: task.label, code, signal }
                handleExit(result)
                resolve(result)
            })
        })
    })

    process.on("SIGINT", () => stopAll("SIGINT"))
    process.on("SIGTERM", () => stopAll("SIGTERM"))
    process.on("exit", () => stopAll("SIGTERM"))

    const results = await Promise.allSettled(exitPromises)

    for (const result of results) {
        if (result.status === "rejected") {
            process.exitCode = 1
            return
        }
    }

    const failure = results
        .filter((entry) => entry.status === "fulfilled")
        .map((entry) => entry.value)
        .find((entry) => entry.signal == null && entry.code !== 0)

    process.exitCode = failure ? failure.code || 1 : 0
}

main().catch((error) => {
    console.error(`[dev] Unexpected error: ${error.message}`)
    stopAll("SIGTERM")
    process.exitCode = 1
})
