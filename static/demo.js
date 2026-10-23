// Démo statique (GitHub Pages) : simule dans le navigateur ce que fait le serveur.
(function () {
  function message(texte, erreur) {
    var main = document.querySelector("main");
    var liste = main.querySelector("ul.messages");
    if (!liste) {
      liste = document.createElement("ul");
      liste.className = "messages";
      main.insertBefore(liste, main.firstChild);
    }
    liste.innerHTML = "";
    var li = document.createElement("li");
    if (erreur) li.className = "error";
    li.textContent = texte;
    liste.appendChild(li);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function nombre(v) {
    return parseFloat(String(v).replace(",", "."));
  }

  function format(v) {
    return (Math.round(v * 100) / 100).toLocaleString("fr-FR");
  }

  document.querySelectorAll("[data-demo-parametrage]").forEach(function (lien) {
    lien.addEventListener("click", function (e) {
      e.preventDefault();
      message("Démo : le paramétrage (création et modification des articles, outils, produits, comptes) se fait dans l'interface d'administration, disponible sur la version installée.");
    });
  });

  // Sortie ou entrée de stock sur la page d'un article.
  var stock = document.getElementById("stock-actuel");
  document.querySelectorAll("form[method=post]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var quantite = form.querySelector("[name=quantite]");
      if (quantite && stock) {
        var q = nombre(quantite.value);
        if (!(q > 0)) return message("Saisissez une quantité positive.", true);
        var type = form.querySelector("[name=type]:checked").value;
        var valeur = nombre(stock.dataset.stock) + (type === "sortie" ? -q : q);
        stock.dataset.stock = valeur;
        var alerte = valeur <= nombre(stock.dataset.mini);
        stock.innerHTML = '<span class="etiquette ' + (alerte ? "alerte" : "ok") + '">' + format(valeur) + " " +
          stock.dataset.unite + (alerte ? " – à commander" : "") + "</span>";
        form.reset();
        return message((type === "sortie" ? "Sortie" : "Entrée") + " de " + format(q) +
          " simulée : nouveau stock " + format(valeur) + ". (Démo : rien n'est enregistré.)");
      }
      var comptes = Array.prototype.filter.call(form.querySelectorAll("input.compte"), function (i) {
        return i.value.trim() !== "";
      });
      if (comptes.length) {
        comptes.forEach(function (i) {
          var ligne = i.closest("tr");
          ligne.cells[2].textContent = i.value + " " + ligne.cells[2].textContent.split(" ").slice(1).join(" ");
          ligne.cells[3].textContent = new Date().toLocaleDateString("fr-FR");
          i.value = "";
        });
        return message(comptes.length + " comptage(s) simulé(s), stocks corrigés à l'écran. (Démo : rien n'est enregistré.)");
      }
      message("Rien à enregistrer.", true);
    });
  });

  // Filtres et recherches : appliqués directement sur le tableau.
  document.querySelectorAll("form.filtres").forEach(function (form) {
    var table = document.querySelector("main table");
    if (!table) return;
    function filtrer(e) {
      if (e) e.preventDefault();
      var texte = (form.querySelector("[type=search]") || { value: "" }).value.trim().toLowerCase();
      var selects = form.querySelectorAll("select");
      var alerte = form.querySelector("[name=alerte]");
      Array.prototype.slice.call(table.rows, 1).forEach(function (ligne) {
        var visible = !texte || ligne.textContent.toLowerCase().indexOf(texte) !== -1;
        selects.forEach(function (s) {
          if (s.value && ligne.dataset[s.name] !== s.value) visible = false;
        });
        if (alerte && alerte.checked && ligne.dataset.alerte !== "1") visible = false;
        ligne.style.display = visible ? "" : "none";
      });
    }
    form.addEventListener("submit", filtrer);
    form.addEventListener("change", filtrer);
    form.addEventListener("input", filtrer);
  });
})();
