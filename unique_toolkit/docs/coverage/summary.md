# Coverage Summary

Generated on: Sat Sep 13 14:22:50 CEST 2025

| Name                                                                            |    Stmts |     Miss |      Cover |   Missing |
|-------------------------------------------------------------------------------- | -------: | -------: | ---------: | --------: |
| unique\_toolkit/\_\_init\_\_.py                                                 |        6 |        0 |    100.00% |           |
| unique\_toolkit/\_common/\_base\_service.py                                     |        7 |        2 |     71.43% |      9-10 |
| unique\_toolkit/\_common/\_time\_utils.py                                       |        3 |        1 |     66.67% |         5 |
| unique\_toolkit/\_common/base\_model\_type\_attribute.py                        |      107 |        7 |     93.46% |37, 44-49, 75-76, 84 |
| unique\_toolkit/\_common/chunk\_relevancy\_sorter/config.py                     |       16 |       16 |      0.00% |      1-41 |
| unique\_toolkit/\_common/chunk\_relevancy\_sorter/exception.py                  |        3 |        3 |      0.00% |       1-5 |
| unique\_toolkit/\_common/chunk\_relevancy\_sorter/schemas.py                    |       31 |       31 |      0.00% |      1-46 |
| unique\_toolkit/\_common/chunk\_relevancy\_sorter/service.py                    |      116 |      116 |      0.00% |     1-372 |
| unique\_toolkit/\_common/default\_language\_model.py                            |        5 |        5 |      0.00% |       1-6 |
| unique\_toolkit/\_common/endpoint\_builder.py                                   |       42 |       42 |      0.00% |     6-176 |
| unique\_toolkit/\_common/endpoint\_requestor.py                                 |       23 |       23 |      0.00% |     1-137 |
| unique\_toolkit/\_common/exception.py                                           |       21 |       21 |      0.00% |      1-33 |
| unique\_toolkit/\_common/feature\_flags/schema.py                               |        5 |        5 |      0.00% |      1-10 |
| unique\_toolkit/\_common/pydantic\_helpers.py                                   |       11 |        1 |     90.91% |        18 |
| unique\_toolkit/\_common/token/image\_token\_counting.py                        |       34 |       34 |      0.00% |      1-67 |
| unique\_toolkit/\_common/token/token\_counting.py                               |       95 |       95 |      0.00% |     4-204 |
| unique\_toolkit/\_common/utils/structured\_output/schema.py                     |        3 |        3 |      0.00% |       1-5 |
| unique\_toolkit/\_common/validate\_required\_values.py                          |        6 |        0 |    100.00% |           |
| unique\_toolkit/\_common/validators.py                                          |       35 |       35 |      0.00% |      1-98 |
| unique\_toolkit/app/\_\_init\_\_.py                                             |       20 |        0 |    100.00% |           |
| unique\_toolkit/app/dev\_util.py                                                |       66 |       46 |     30.30% |24-27, 57-78, 93-102, 119-131, 135-138, 157-170 |
| unique\_toolkit/app/init\_logging.py                                            |        8 |        1 |     87.50% |        31 |
| unique\_toolkit/app/init\_sdk.py                                                |       34 |       19 |     44.12% |25-29, 43-51, 64-66, 71-72 |
| unique\_toolkit/app/performance/async\_tasks.py                                 |       29 |        0 |    100.00% |           |
| unique\_toolkit/app/performance/async\_wrapper.py                               |       17 |        6 |     64.71% |12-18, 35-39 |
| unique\_toolkit/app/schemas.py                                                  |      126 |       18 |     85.71% |43-47, 206-207, 228-232, 238, 258-262 |
| unique\_toolkit/app/unique\_settings.py                                         |      105 |       31 |     70.48% |107-121, 124-125, 128-130, 199-214, 259-268, 276-278, 294-296 |
| unique\_toolkit/app/verification.py                                             |       50 |       37 |     26.00% |46-64, 74-112 |
| unique\_toolkit/chat/\_\_init\_\_.py                                            |        9 |        0 |    100.00% |           |
| unique\_toolkit/chat/constants.py                                               |        3 |        0 |    100.00% |           |
| unique\_toolkit/chat/functions.py                                               |      251 |       80 |     68.13% |191, 228-230, 376, 568-570, 617-619, 663-665, 709-711, 819-821, 950-969, 1003-1022, 1056-1075, 1109-1128, 1158-1171, 1201-1214, 1236-1245, 1267-1276, 1304-1316, 1344-1356 |
| unique\_toolkit/chat/schemas.py                                                 |      132 |       12 |     90.91% |47, 61, 98, 102-130 |
| unique\_toolkit/chat/service.py                                                 |      189 |       44 |     76.72% |98, 124, 150, 176, 202, 228, 254, 280, 289, 308, 326, 361, 400, 501, 513, 529, 706-720, 746-760, 944, 984, 1024, 1064, 1104, 1142, 1174, 1206, 1232, 1254, 1282, 1313, 1344, 1373, 1392, 1406, 1432, 1461, 1536-1548, 1618-1630 |
| unique\_toolkit/chat/state.py                                                   |       16 |       16 |      0.00% |      1-41 |
| unique\_toolkit/chat/utils.py                                                   |       11 |        8 |     27.27% |     17-25 |
| unique\_toolkit/content/\_\_init\_\_.py                                         |       14 |        0 |    100.00% |           |
| unique\_toolkit/content/constants.py                                            |        2 |        0 |    100.00% |           |
| unique\_toolkit/content/functions.py                                            |      145 |       18 |     87.59% |60, 108, 155, 179, 257-259, 394-396, 402, 416, 531-533, 575-577 |
| unique\_toolkit/content/schemas.py                                              |       74 |        0 |    100.00% |           |
| unique\_toolkit/content/service.py                                              |      181 |       36 |     80.11% |122-129, 146-151, 168, 194, 220, 246, 272, 665-678, 681-694, 697-702, 705-710 |
| unique\_toolkit/content/utils.py                                                |       81 |        5 |     93.83% |119, 121, 123, 165-166 |
| unique\_toolkit/debug\_info\_manager/debug\_info\_manager.py                    |       11 |       11 |      0.00% |      1-18 |
| unique\_toolkit/embedding/\_\_init\_\_.py                                       |        4 |        0 |    100.00% |           |
| unique\_toolkit/embedding/constants.py                                          |        2 |        0 |    100.00% |           |
| unique\_toolkit/embedding/functions.py                                          |       21 |        0 |    100.00% |           |
| unique\_toolkit/embedding/schemas.py                                            |        3 |        0 |    100.00% |           |
| unique\_toolkit/embedding/service.py                                            |       59 |       14 |     76.27% |47-49, 56, 64-69, 85, 98, 111, 124, 137 |
| unique\_toolkit/embedding/utils.py                                              |        3 |        1 |     66.67% |         9 |
| unique\_toolkit/evals/config.py                                                 |       16 |       16 |      0.00% |      1-35 |
| unique\_toolkit/evals/context\_relevancy/prompts.py                             |        4 |        4 |      0.00% |      1-44 |
| unique\_toolkit/evals/context\_relevancy/schema.py                              |       25 |       25 |      0.00% |      1-68 |
| unique\_toolkit/evals/context\_relevancy/service.py                             |       83 |       83 |      0.00% |     1-270 |
| unique\_toolkit/evals/evaluation\_manager.py                                    |       58 |       58 |      0.00% |     1-207 |
| unique\_toolkit/evals/exception.py                                              |        3 |        3 |      0.00% |       1-5 |
| unique\_toolkit/evals/hallucination/constants.py                                |       22 |       22 |      0.00% |      1-56 |
| unique\_toolkit/evals/hallucination/hallucination\_evaluation.py                |       29 |       29 |      0.00% |      1-82 |
| unique\_toolkit/evals/hallucination/prompts.py                                  |        4 |        4 |      0.00% |      1-65 |
| unique\_toolkit/evals/hallucination/service.py                                  |       19 |       19 |      0.00% |      1-54 |
| unique\_toolkit/evals/hallucination/utils.py                                    |       63 |       63 |      0.00% |     1-212 |
| unique\_toolkit/evals/output\_parser.py                                         |       13 |       13 |      0.00% |      1-43 |
| unique\_toolkit/evals/schemas.py                                                |       54 |       54 |      0.00% |     1-101 |
| unique\_toolkit/framework\_utilities/\_\_init\_\_.py                            |        0 |        0 |    100.00% |           |
| unique\_toolkit/framework\_utilities/langchain/client.py                        |       15 |       15 |      0.00% |      1-42 |
| unique\_toolkit/framework\_utilities/langchain/history.py                       |       12 |       12 |      0.00% |      1-19 |
| unique\_toolkit/framework\_utilities/openai/\_\_init\_\_.py                     |        3 |        3 |      0.00% |       3-6 |
| unique\_toolkit/framework\_utilities/openai/client.py                           |       21 |       21 |      0.00% |      1-68 |
| unique\_toolkit/framework\_utilities/openai/message\_builder.py                 |       45 |       45 |      0.00% |     1-145 |
| unique\_toolkit/framework\_utilities/utils.py                                   |       11 |       11 |      0.00% |      1-23 |
| unique\_toolkit/history\_manager/history\_construction\_with\_contents.py       |      132 |      132 |      0.00% |     1-295 |
| unique\_toolkit/history\_manager/history\_manager.py                            |       63 |       63 |      0.00% |     1-217 |
| unique\_toolkit/history\_manager/loop\_token\_reducer.py                        |      174 |      174 |      0.00% |     1-481 |
| unique\_toolkit/history\_manager/utils.py                                       |       56 |       56 |      0.00% |     1-159 |
| unique\_toolkit/language\_model/\_\_init\_\_.py                                 |       25 |        0 |    100.00% |           |
| unique\_toolkit/language\_model/builder.py                                      |       43 |        5 |     88.37% |21-22, 25-27 |
| unique\_toolkit/language\_model/constants.py                                    |        4 |        0 |    100.00% |           |
| unique\_toolkit/language\_model/functions.py                                    |      111 |       38 |     65.77% |89-91, 234, 279-299, 304-308, 363-372, 379, 404-414, 435-446, 458-494 |
| unique\_toolkit/language\_model/infos.py                                        |      270 |       23 |     91.48% |72-109, 1125-1131, 1143-1146, 1177, 1191-1194, 1279 |
| unique\_toolkit/language\_model/prompt.py                                       |       24 |        0 |    100.00% |           |
| unique\_toolkit/language\_model/reference.py                                    |       91 |       78 |     14.29% |17-31, 45-71, 77-131, 137-145, 151-158, 163-164, 173-221, 226-227, 232-237, 242 |
| unique\_toolkit/language\_model/schemas.py                                      |      241 |       44 |     81.74% |87-93, 97-109, 112-118, 137, 140, 186-187, 230, 244-255, 336, 339, 373-379, 401-404, 407-410, 429, 505 |
| unique\_toolkit/language\_model/service.py                                      |      101 |       14 |     86.14% |91, 98-103, 119, 145, 171, 197, 223, 299, 324, 348 |
| unique\_toolkit/language\_model/utils.py                                        |       22 |        0 |    100.00% |           |
| unique\_toolkit/postprocessor/postprocessor\_manager.py                         |       40 |       40 |      0.00% |     1-120 |
| unique\_toolkit/protocols/support.py                                            |        4 |        4 |      0.00% |      1-12 |
| unique\_toolkit/reference\_manager/reference\_manager.py                        |       49 |       49 |      0.00% |     1-103 |
| unique\_toolkit/short\_term\_memory/\_\_init\_\_.py                             |        3 |        0 |    100.00% |           |
| unique\_toolkit/short\_term\_memory/constants.py                                |        1 |        0 |    100.00% |           |
| unique\_toolkit/short\_term\_memory/functions.py                                |       42 |       26 |     38.10% |35-47, 73-85, 128-130, 159-175 |
| unique\_toolkit/short\_term\_memory/persistent\_short\_term\_memory\_manager.py |       60 |       60 |      0.00% |     1-141 |
| unique\_toolkit/short\_term\_memory/schemas.py                                  |       29 |        3 |     89.66% | 33-34, 49 |
| unique\_toolkit/short\_term\_memory/service.py                                  |       87 |       22 |     74.71% |57-61, 66, 78, 96, 109, 122, 135, 148, 161, 174, 187, 200, 205, 226, 248, 271, 294, 316 |
| unique\_toolkit/smart\_rules/\_\_init\_\_.py                                    |        0 |        0 |    100.00% |           |
| unique\_toolkit/smart\_rules/compile.py                                         |      147 |       22 |     85.03% |55, 119, 139, 142-147, 155-157, 173-177, 185, 196-198, 209, 219, 252, 285 |
| unique\_toolkit/thinking\_manager/thinking\_manager.py                          |       47 |       47 |      0.00% |     1-103 |
| unique\_toolkit/tools/\_\_init\_\_.py                                           |        0 |        0 |    100.00% |           |
| unique\_toolkit/tools/a2a/\_\_init\_\_.py                                       |        3 |        3 |      0.00% |       1-4 |
| unique\_toolkit/tools/a2a/config.py                                             |       17 |       17 |      0.00% |      1-27 |
| unique\_toolkit/tools/a2a/manager.py                                            |       23 |       23 |      0.00% |      1-49 |
| unique\_toolkit/tools/a2a/memory.py                                             |        9 |        9 |      0.00% |      1-26 |
| unique\_toolkit/tools/a2a/schema.py                                             |        8 |        8 |      0.00% |      1-15 |
| unique\_toolkit/tools/a2a/service.py                                            |       63 |       63 |      0.00% |     1-156 |
| unique\_toolkit/tools/agent\_chunks\_hanlder.py                                 |       40 |       40 |      0.00% |      1-65 |
| unique\_toolkit/tools/config.py                                                 |       61 |       61 |      0.00% |     1-132 |
| unique\_toolkit/tools/factory.py                                                |       26 |       26 |      0.00% |      1-40 |
| unique\_toolkit/tools/mcp/\_\_init\_\_.py                                       |        3 |        3 |      0.00% |       1-4 |
| unique\_toolkit/tools/mcp/manager.py                                            |       33 |       33 |      0.00% |      1-67 |
| unique\_toolkit/tools/mcp/models.py                                             |       19 |       19 |      0.00% |      1-28 |
| unique\_toolkit/tools/mcp/tool\_wrapper.py                                      |       95 |       95 |      0.00% |     1-262 |
| unique\_toolkit/tools/schemas.py                                                |       72 |       72 |      0.00% |     1-141 |
| unique\_toolkit/tools/tool.py                                                   |       74 |       74 |      0.00% |     1-180 |
| unique\_toolkit/tools/tool\_manager.py                                          |      131 |      131 |      0.00% |     1-295 |
| unique\_toolkit/tools/tool\_progress\_reporter.py                               |       87 |       87 |      0.00% |     1-219 |
| unique\_toolkit/tools/utils/\_\_init\_\_.py                                     |        0 |        0 |    100.00% |           |
| unique\_toolkit/tools/utils/execution/\_\_init\_\_.py                           |        0 |        0 |    100.00% |           |
| unique\_toolkit/tools/utils/execution/execution.py                              |       69 |       69 |      0.00% |     1-282 |
| unique\_toolkit/tools/utils/source\_handling/\_\_init\_\_.py                    |        0 |        0 |    100.00% |           |
| unique\_toolkit/tools/utils/source\_handling/schema.py                          |       11 |       11 |      0.00% |      2-21 |
| unique\_toolkit/tools/utils/source\_handling/source\_formatting.py              |       42 |       42 |      0.00% |     1-207 |
|                                                                       **TOTAL** | **5487** | **3129** | **42.97%** |           |

## Additional Coverage Tools

- **[Diff Coverage](diff_coverage.md)** - PR-focused coverage checking for new/modified code (integrated in CI/CD)
