## 改动说明

<!-- 为什么改、解决什么问题。关联 Issue 用 Fixes #123 -->

## 改动类型

- [ ] 缺陷修复
- [ ] 新功能
- [ ] 性能优化
- [ ] 重构 / 代码清理
- [ ] 文档
- [ ] 测试 / 构建

## 验证方式

请勾选实际执行过的项（命令与约定见 `CONTRIBUTING.md`）：

- [ ] `cd api && .venv/bin/python -m pytest -q` 通过
- [ ] `cd frontend && npm run build` 通过
- [ ] `cd frontend && npx playwright test` 通过（隔离环境 E2E）
- [ ] 改动涉及前后端代码时，已重建本机部署并跑 `npx playwright test --config playwright.live.config.ts` 通过
- [ ] 以上均未执行（仅文档改动等），说明：

## 检查项

- [ ] 新增或修改的接口已同步 `docs/API接口文档.md`
- [ ] 列表页带分页控件且分页栏靠左（每页条数 → 总数 → 页码），见 `AGENTS.md`
- [ ] 选择业务对象使用统一控件 `frontend/src/components/EntitySelect.vue`，候选数据来自 `GET /api/options/{entity}`
- [ ] 未提交密钥、真实业务数据、生产环境地址等敏感信息
- [ ] 提交信息符合 `类型(范围): 说明` 约定

## 其它说明

<!-- 兼容性影响、数据库变更、部署注意事项等 -->
