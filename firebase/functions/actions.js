/* eslint-disable indent */
/* eslint-disable  require-jsdoc */
/* eslint-disable  arrow-parens */
/* eslint-disable  quotes */
/* eslint-disable  max-len */

const functions = require("firebase-functions");
const admin = require('firebase-admin');
const {FieldValue} = require("firebase-admin/firestore");

admin.initializeApp();

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function read(userId, taskId) {
    let completedTask = null;
    const db = admin.firestore();
    await db.collection("userTasks").doc(userId).collection("tasks").get().then(snapshot => {
        snapshot.forEach(doc => {
            const task = {
                "taskId": doc.id,
                "request": doc.data().request,
                "result": doc.data().result,
                "status": doc.data().status,
                "links": doc.data().links,
            };
            if (task["taskId"] === taskId && task["status"] === "COMPLETED") {
                completedTask = task;
            }
        });
    }).catch(reason => {
        console.log("processAction error: " + reason);
        console.error(reason);
    });
    return completedTask;
}

async function readWithLinks(userId, taskId) {
    let completedTask = null;
    const db = admin.firestore();
    await db.collection("userTasks").doc(userId).collection("tasks").get().then(snapshot => {
        snapshot.forEach(doc => {
            const task = {
                "taskId": doc.id,
                "request": doc.data().request,
                "result": doc.data().result,
                "status": doc.data().status,
                "links": doc.data().links,
            };
            if (task["taskId"] === taskId && task["status"] === "COMPLETED") {
                completedTask = task;
            }
        });
    }).catch(reason => {
        console.log("processAction error: " + reason);
        console.error(reason);
    });
    return completedTask;
}

exports.processAction = functions.https.onRequest(
    async (req, res,
    ) => {
        try {
            let readyTask = null;
            const userId = req.query["userId"];
            const question = req.query["question"];

            const newTask = {
                "status": "PENDING",
                "request": question,
                "createdAt": FieldValue.serverTimestamp(),
            };
            let newTaskId = null;
            await admin.firestore().collection('userTasks').doc(userId).collection("tasks").add(newTask).then(writeResult => {
                newTaskId = writeResult.id;
                console.log("created task successfully: " + JSON.stringify(newTask));
                console.log("created task successfully with result: " + writeResult);
            });
            let count = 0;
            const retryLimit = 100;
            if (newTaskId) {
                while (!readyTask) {
                    count++;
                    console.log("task is pending. count: " + count);
                    if (count === retryLimit) {
                        // noinspection ExceptionCaughtLocallyJS
                        throw new Error("Too many retries for request");
                    }
                    readyTask = await read(userId, newTaskId);
                    await sleep(500);
                }
            } else {
                throw new Error("unable to create new task");
            }

            console.log("task is ready! task content: " + JSON.stringify(newTask));

            const result = {
                "status": "ok",
                "localAnswer": readyTask["result"],
                "links": readyTask["links"],
            };
            res.status(200).send(result);
            return {
                result: result,
            };
        } catch (error) {
            console.log("processAction error: " + error);
            console.error(error);
            res.status(500).send({
                "status": "error",
                "answer": "issue processing the request" + error + " request: " + JSON.stringify(req),
            });
        }
    });


exports.processAction2 = functions.https.onRequest(
    async (req, res,
    ) => {
        try {
            let readyTask = null;
            const userId = req.query["userId"];
            const question = req.query["question"];

            const newTask = {
                "status": "PENDING",
                "request": question,
                "createdAt": FieldValue.serverTimestamp(),
            };
            let newTaskId = null;
            await admin.firestore().collection('userTasks').doc(userId).collection("tasks").add(newTask).then(writeResult => {
                newTaskId = writeResult.id;
                console.log("created task successfully: " + JSON.stringify(newTask));
                console.log("created task successfully with result: " + writeResult);
            });
            let count = 0;
            const retryLimit = 100;
            if (newTaskId) {
                while (!readyTask) {
                    count++;
                    console.log("task is pending. count: " + count);
                    if (count === retryLimit) {
                        // noinspection ExceptionCaughtLocallyJS
                        throw new Error("Too many retries for request");
                    }
                    readyTask = await readWithLinks(userId, newTaskId);
                    await sleep(500);
                }
            } else {
                throw new Error("unable to create new task");
            }

            console.log("task is ready! task content: " + JSON.stringify(newTask));

            const result = {
                "status": "ok",
                "localAnswer": readyTask["result"],
                "links": readyTask["links"],
            };
            res.status(200).send(result);
            return {
                result: result,
            };
        } catch (error) {
            console.log("processAction error: " + error);
            console.error(error);
            res.status(500).send({
                "status": "error",
                "answer": "issue processing the request" + error + " request: " + JSON.stringify(req),
            });
        }
    });
