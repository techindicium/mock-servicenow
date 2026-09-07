(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DirectoryLogic = factory();
})(typeof window !== "undefined" ? window : globalThis, function () {
  function userRowCells(user) {
    return {
      name: user.name,
      role: user.role,
      assignment_group: user.assignment_group === null || user.assignment_group === undefined
        ? ""
        : user.assignment_group,
    };
  }

  function groupRowCells(group) {
    return { name: group.name };
  }

  return { userRowCells, groupRowCells };
});
