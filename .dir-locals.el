((org-mode
  .
  ((eval .
         (setq-local
          org-publish-project-alist
          `(
            ("doc" :components ("doc-org" "doc-static"))
            ("doc-org"
             ;; Path to org files.
             :base-directory ,(expand-file-name "org" (projectile-project-root))
             :base-extension "org"
             ;; Path to Jekyll Posts
             :publishing-directory ,(projectile-project-root)
             :recursive t
             :publishing-function org-html-publish-to-html
             :headline-levels 4
             :html-extension "html"
             :body-only t
             )
            ("doc-static"
             :base-directory ,(expand-file-name "org" (projectile-project-root))
             :base-extension "css\\|js\\|png\\|jpg\\|gif\\|pdf\\|mp3\\|ogg\\|swf\\|php"
             :publishing-directory ,(projectile-project-root)
             :recursive t
             :publishing-function org-publish-attachment)
            )
          )))))
