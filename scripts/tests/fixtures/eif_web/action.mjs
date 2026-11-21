export function actionButton(label, activate) {
  const button = document.createElement("button");
  button.type = "button";
  button.id = "retry";
  button.className = "action";
  button.textContent = label;
  button.addEventListener("click", activate);
  return button;
}
