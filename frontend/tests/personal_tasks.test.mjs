import assert from "node:assert/strict"
import {after,before,test} from "node:test"
import React from "react"
import {renderToStaticMarkup} from "react-dom/server"
import reactPlugin from "@vitejs/plugin-react"
import {createServer} from "vite"
let vite,service,Panel
before(async()=>{vite=await createServer({configFile:false,root:process.cwd(),plugins:[reactPlugin()],server:{middlewareMode:true},appType:"custom",logLevel:"error"});service=await vite.ssrLoadModule("/src/api/tasks.ts");({default:Panel}=await vite.ssrLoadModule("/src/components/PersonalTasksPanel.tsx"))})
after(async()=>{await vite?.close()})
function setup(){const requests=[];globalThis.window={localStorage:{getItem:()=>null},dispatchEvent(){},location:{search:""}};globalThis.document={cookie:""};globalThis.fetch=async(url,init={})=>{requests.push({url:String(url),method:init.method??"GET",body:init.body?JSON.parse(init.body):undefined});return new Response(init.method==="DELETE"?null:"{}",{status:init.method==="DELETE"?204:200,headers:{"Content-Type":"application/json"}})};return requests}
test("task filters combine text, category, uncategorized and status parameters",async()=>{const r=setup();await service.listPersonalTasks({q:" algebra ",category:"Revision",status:"overdue"});assert.equal(r[0].url,"/api/me/tasks?q=algebra&category=Revision&status=overdue");await service.listPersonalTasks({category:"__uncategorized__",status:"open"});assert.equal(r[1].url,"/api/me/tasks?uncategorized=true&status=open")})
test("task service calls private summary and CRUD endpoints",async()=>{const r=setup(),p={title:"Read chapter",description:"",category:null,due_date:null,completed:false};await service.getPersonalTaskSummary();await service.createPersonalTask(p);await service.updatePersonalTask(14,{...p,completed:true});await service.deletePersonalTask(14);assert.deepEqual(r.map(x=>[x.url,x.method]),[["/api/me/tasks/summary","GET"],["/api/me/tasks","POST"],["/api/me/tasks/14","PUT"],["/api/me/tasks/14","DELETE"]])})
test("task panel exposes task search, category and status filters plus summaries",()=>{globalThis.window={location:{search:""}};const html=renderToStaticMarkup(React.createElement(Panel));for(const label of ["Personal learning tasks","Open tasks","Completed tasks","Overdue tasks","Uncategorized","Search tasks","Add task"])assert.match(html,new RegExp(label))})
