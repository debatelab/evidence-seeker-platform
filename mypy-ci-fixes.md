# MyPy CI Fixes Checklist

## Files to Fix:
- [ ] app/schemas/user.py (3 unused type: ignore comments)
- [ ] app/core/auth.py (2 unused type: ignore + 1 type compatibility issue)
- [ ] app/core/embedding_service.py (5 unused type: ignore + 2 type issues)
- [ ] tests/conftest.py (1 unused type: ignore)

## Specific Issues:
### app/schemas/user.py
- [ ] Line 8: Remove unused "type: ignore" comment
- [ ] Line 32: Remove unused "type: ignore" comment
- [ ] Line 123: Remove unused "type: ignore" comment

### app/core/auth.py
- [ ] Line 97: Remove unused "type: ignore" comment
- [ ] Line 118: Remove unused "type: ignore" comment and fix type compatibility issue

### app/core/embedding_service.py
- [ ] Line 53: Remove unused "type: ignore" comment
- [ ] Line 95: Fix incompatible types in assignment
- [ ] Line 111: Remove unused "type: ignore" comment
- [ ] Line 235: Remove unused "type: ignore" comment
- [ ] Line 236: Fix Any return type and union attribute access issues
- [ ] Line 243: Remove unused "type: ignore" comment
- [ ] Line 244: Remove unused "type: ignore" comment

### tests/conftest.py
- [ ] Line 346: Remove unused "type: ignore" comment
