// app.js — small helpers for CloudCart (vanilla JavaScript only).
//
// 1. Live image preview on the Add Product page: when the user
//    picks a file, show it right away, before uploading.
// 2. A quick client-side size check (5 MB) so the user gets a
//    friendly message before the form is sent. The server checks
//    again — client checks are never trusted on their own.

document.addEventListener("DOMContentLoaded", function () {
  var input = document.getElementById("image-input");
  var preview = document.getElementById("image-preview");
  if (!input || !preview) return;

  input.addEventListener("change", function () {
    var file = input.files[0];
    if (!file) {
      preview.classList.add("d-none");
      return;
    }
    // 5 MB limit, checked here for a fast message.
    if (file.size > 5 * 1024 * 1024) {
      alert("Image is too large. Maximum size is 5 MB.");
      input.value = "";
      preview.classList.add("d-none");
      return;
    }
    // Show the chosen image immediately.
    var reader = new FileReader();
    reader.onload = function (event) {
      preview.src = event.target.result;
      preview.classList.remove("d-none");
    };
    reader.readAsDataURL(file);
  });
});
