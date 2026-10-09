<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { employeeApi } from '@/api/org'
import { statusTagMap } from '@/utils/constants'

const config = {
  title: '员工管理',
  api: employeeApi,
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'code', label: '工号', width: 110 },
    { prop: 'name', label: '姓名', width: 110 },
    { prop: 'gender', label: '性别', width: 80 },
    { prop: 'position', label: '职位', width: 150 },
    { prop: 'department_id', label: '部门 ID', width: 100 },
    { prop: 'hire_date', label: '入职日期', type: 'date', width: 120 },
    { prop: 'employment_status', label: '状态', type: 'tag', tagMap: statusTagMap, width: 100 },
    { prop: 'phone', label: '电话', width: 130 },
  ],
  searchFields: [
    { prop: 'keyword', label: '关键词' },
    { prop: 'employment_status', label: '状态', type: 'select', options: [{ label: '在职', value: '在职' }, { label: '离职', value: '离职' }] },
  ],
  formFields: [
    { prop: 'code', label: '工号', type: 'input', required: true, span: 12 },
    { prop: 'name', label: '姓名', type: 'input', required: true, span: 12 },
    { prop: 'gender', label: '性别', type: 'select', options: [{ label: '男', value: '男' }, { label: '女', value: '女' }], span: 12 },
    { prop: 'department_id', label: '部门 ID', type: 'number', required: true, span: 12 },
    { prop: 'position', label: '职位', type: 'input', span: 12 },
    { prop: 'manager_id', label: '上级员工 ID', type: 'input', nullable: true, span: 12 },
    { prop: 'hire_date', label: '入职日期', type: 'date', required: true, span: 12 },
    { prop: 'employment_status', label: '在职状态', type: 'select', default: '在职', options: [{ label: '在职', value: '在职' }, { label: '离职', value: '离职' }], span: 12 },
    { prop: 'phone', label: '电话', type: 'input', span: 12 },
    { prop: 'email', label: '邮箱', type: 'input', span: 12 },
  ],
}
</script>
<template>
  <CrudPage v-bind="config" />
</template>
