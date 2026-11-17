import assert from "node:assert/strict"
import {before,after,test} from "node:test"
import {resolve} from "node:path"
import {loadWithRspack} from "./rspack-test-utils.mjs"
let cleanup,service
before(async()=>{
  const loaded=await loadWithRspack({source:`import * as service from ${JSON.stringify(resolve(process.cwd(),"src/api/groups.ts"))}; export {service}`})
  cleanup=loaded.cleanup
  service=loaded.exports.service
})
after(async()=>{await cleanup?.()})
function setup(){const requests=[];globalThis.window={localStorage:{getItem:()=>null},dispatchEvent(){},location:{search:""}};globalThis.document={cookie:""};globalThis.fetch=async(url,init={})=>{requests.push({url:String(url),method:init.method??"GET",body:init.body?JSON.parse(init.body):undefined});return new Response(init.method==="DELETE"?null:"{}",{status:init.method==="DELETE"?204:200,headers:{"Content-Type":"application/json"}})};return requests}
test("group service uses authenticated group and membership endpoints",async()=>{const r=setup();await service.listGroups();await service.getGroup(7);await service.createGroup({name:"Batch A",description:"Physics"});await service.addGroupMember(7,"student@example.com");await service.removeGroupMember(7,12);assert.deepEqual(r.map(x=>[x.url,x.method]),[["/api/groups","GET"],["/api/groups/7","GET"],["/api/groups","POST"],["/api/groups/7/members","POST"],["/api/groups/7/members/12","DELETE"]]);assert.deepEqual(r[2].body,{name:"Batch A",description:"Physics"});assert.deepEqual(r[3].body,{student_email:"student@example.com"})})
test("group task service sends assignment targeting and own completion updates",async()=>{const r=setup();const task={title:"Chapter 2",description:"Exercises",video_url:"https://drive.google.com/file/d/abc123/view",due_date:"2026-12-01"};await service.createGroupTask(7,task);await service.updateGroupTask(7,3,task);await service.assignGroupTask(7,3,false,[12,13]);await service.updateGroupTaskCompletion(7,3,true);await service.deleteGroupTask(7,3);assert.deepEqual(r.map(x=>[x.url,x.method]),[["/api/groups/7/tasks","POST"],["/api/groups/7/tasks/3","PUT"],["/api/groups/7/tasks/3/assignments","POST"],["/api/groups/7/tasks/3/completion","PATCH"],["/api/groups/7/tasks/3","DELETE"]]);assert.deepEqual(r[0].body,task);assert.deepEqual(r[1].body,task);assert.deepEqual(r[2].body,{all_members:false,student_account_ids:[12,13]});assert.deepEqual(r[3].body,{completed:true})})
test("member permission service sends explicit independent capabilities",async()=>{const r=setup();await service.setGroupMemberPermissions(7,12,{can_create_tasks:true,can_edit_tasks:false,can_assign_tasks:true});assert.equal(r[0].url,"/api/groups/7/members/12/permissions");assert.deepEqual(r[0].body,{can_create_tasks:true,can_edit_tasks:false,can_assign_tasks:true})})
